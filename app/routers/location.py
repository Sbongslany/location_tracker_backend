

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List
from app.models.location import Location
from app.database.db import get_db
# Corrected import for get_current_user, SECRET_KEY, and ALGORITHM
from app.utils.auth import get_current_user, SECRET_KEY, ALGORITHM
from app.models.user import UserResponse
from collections import defaultdict
import json
from jose import jwt # For JWT decoding

router = APIRouter(
    # Removed prefix="/location" to define full paths directly for clarity
    # If you intend to use a prefix, then the endpoint paths below
    # would need to be adjusted (e.g., @router.post("/") if prefix is /location)
    # For this solution, we define full paths.
    tags=["locations"],
    responses={404: {"description": "Not found"}, 401: {"description": "Unauthorized"}}
)

# WebSocket connections storage, keyed by user_id
connected_clients = defaultdict(list)

@router.post("/location", status_code=201)
async def create_location(location: Location, current_user: UserResponse = Depends(get_current_user)):
    """Fallback HTTP endpoint for location data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO locations (user_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)",
                (current_user.id, location.latitude, location.longitude, location.timestamp)
            )
            conn.commit()
        return {"message": "Location saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save location: {str(e)}")

@router.get("/locations", response_model=List[Location]) # Changed to /locations (no trailing slash)
async def get_locations(current_user: UserResponse = Depends(get_current_user)):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM locations WHERE user_id = ? ORDER BY timestamp DESC", (current_user.id,))
            rows = cursor.fetchall()
            # Assuming Location model can be initialized from dict rows directly
            return [Location(**dict(row)) for row in rows] # Use dict(row) to convert sqlite3.Row to dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch locations: {str(e)}")

@router.websocket("/ws") # This route is now just /ws, assuming no prefix
async def websocket_location(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time location updates"""
    # Verify JWT token
    try:
        # Use the directly imported SECRET_KEY and ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id") # Assuming 'user_id' is in your JWT payload
        if email is None or user_id is None:
            await websocket.close(code=1008, reason="Invalid token: Missing email or user_id")
            return

        # Ensure user_id is an integer
        try:
            user_id = int(user_id)
        except ValueError:
            await websocket.close(code=1008, reason="Invalid token: user_id is not an integer")
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email FROM users WHERE id = ? AND email = ?", (user_id, email))
            if not cursor.fetchone():
                await websocket.close(code=1008, reason="User not found for token")
                return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token has expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as e:
        await websocket.close(code=1008, reason=f"Token verification failed: {str(e)}")
        return

    # Accept WebSocket connection
    await websocket.accept()
    connected_clients[user_id].append(websocket)
    print(f"User {user_id} connected via WebSocket. Total connections for user: {len(connected_clients[user_id])}")


    try:
        while True:
            try:
                # Receive location data
                data = await websocket.receive_json()
                location = Location(**data)

                # Validate user_id in payload matches the authenticated user_id
                if location.user_id != user_id:
                    await websocket.send_json({"error": "Unauthorized: user_id mismatch in payload"})
                    continue # Continue listening for messages

                # Store in database
                with get_db() as conn:
                    cursor = conn.cursor() # Assuming get_db returns a direct connection object
                    cursor.execute(
                        "INSERT INTO locations (user_id, latitude, longitude, timestamp) VALUES (?, ?, ?, ?)",
                        (user_id, location.latitude, location.longitude, location.timestamp)
                    )
                    conn.commit()

                # Broadcast to all clients for this user_id
                for client in connected_clients[user_id]:
                    # Only send to other clients, not the sender unless desired
                    # if client != websocket:
                    await client.send_json(data)


                # Send acknowledgment to sender
                await websocket.send_json({"message": "Location received successfully"})

            except WebSocketDisconnect:
                print(f"User {user_id} disconnected from WebSocket.")
                break
            except json.JSONDecodeError:
                print(f"User {user_id}: Received invalid JSON.")
                await websocket.send_json({"error": "Invalid JSON format received"})
            except Exception as e:
                print(f"User {user_id}: Failed to process location: {str(e)}")
                await websocket.send_json({"error": f"Failed to process location: {str(e)}"})
    finally:
        # Cleanup: Remove client from connected_clients
        if websocket in connected_clients[user_id]:
            connected_clients[user_id].remove(websocket)
            if not connected_clients[user_id]:
                del connected_clients[user_id] # Clean up if no more clients for this user
        await websocket.close() # Ensure the connection is closed