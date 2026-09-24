# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from google.adk.tools import ToolContext
from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-fde96ef80536"
GCS_BUCKET_NAME = "tricoach-ai-public-4798"


# Initialize Firestore client with hardcoded project ID
db = firestore.Client(project=FIRESTORE_PROJECT_ID)
workouts_ref = db.collection("workouts")


def log_workout(
    activity_type: str,
    title: str,
    duration_minutes: float,
    distance_miles: float,
    date: Optional[str] = None,
    perceived_exertion: Optional[int] = 7,
    notes: Optional[str] = "",
) -> Dict[str, str]:
    """Logs a new workout session into the athlete's workout log in Firestore.

    Args:
        activity_type: The type of workout (e.g. 'swim', 'bike', 'run', or 'strength').
        title: Short title describing the session (e.g. 'Morning Interval Run', 'Base Lake Swim').
        duration_minutes: Duration of the workout in minutes.
        distance_miles: Distance covered in miles (use 0 for stationary/gym sessions).
        date: Date of the workout in YYYY-MM-DD format (defaults to today if omitted).
        perceived_exertion: Rate of Perceived Exertion scale 1-10 (default: 7).
        notes: Additional notes on how the session felt or workout details.

    Returns:
        A dictionary confirming the created workout record with its document ID.
    """
    if not date:
        date = datetime.date.today().isoformat()

    doc_ref = workouts_ref.document()
    workout_id = doc_ref.id

    data = {
        "workout_id": workout_id,
        "activity_type": activity_type.lower(),
        "title": title,
        "duration_minutes": float(duration_minutes),
        "distance_miles": float(distance_miles),
        "date": date,
        "perceived_exertion": int(perceived_exertion or 7),
        "notes": notes or "",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    doc_ref.set(data)
    return {
        "status": "success",
        "workout_id": workout_id,
        "message": f"Successfully logged {activity_type} workout '{title}' on {date}.",
    }


def query_workout_history(
    activity_type: Optional[str] = None, limit: int = 5
) -> List[Dict[str, Any]]:
    """Queries recent workout logs from Firestore for the athlete.

    Args:
        activity_type: Optional filter by activity type ('swim', 'bike', 'run', 'strength').
        limit: Maximum number of recent workouts to retrieve (default: 5).

    Returns:
        A list of workout records ordered by date.
    """
    query = workouts_ref

    if activity_type:
        query = query.where("activity_type", "==", activity_type.lower())

    docs = query.limit(limit).stream()
    results = [doc.to_dict() for doc in docs]

    # Sort descending by date
    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results


def calculate_training_zones(
    ftp_watts: Optional[float] = None, max_hr: Optional[int] = None
) -> Dict[str, Any]:
    """Calculates target heart rate and power training zones for an athlete.

    Args:
        ftp_watts: Functional Threshold Power in Watts (optional).
        max_hr: Maximum Heart Rate in beats per minute (optional).

    Returns:
        A dictionary containing calculated heart rate zones (Z1-Z5) and power zones (Z1-Z5).
    """
    result: Dict[str, Any] = {}

    if max_hr and max_hr > 0:
        result["heart_rate_zones_bpm"] = {
            "Z1_ActiveRecovery": f"{int(max_hr * 0.50)}-{int(max_hr * 0.60)} bpm",
            "Z2_Endurance": f"{int(max_hr * 0.60)}-{int(max_hr * 0.70)} bpm",
            "Z3_Tempo": f"{int(max_hr * 0.70)}-{int(max_hr * 0.80)} bpm",
            "Z4_Threshold": f"{int(max_hr * 0.80)}-{int(max_hr * 0.90)} bpm",
            "Z5_Anaerobic": f"{int(max_hr * 0.90)}-{max_hr} bpm",
        }

    if ftp_watts and ftp_watts > 0:
        result["power_zones_watts"] = {
            "Z1_ActiveRecovery": f"< {int(ftp_watts * 0.55)} W",
            "Z2_Endurance": f"{int(ftp_watts * 0.55)}-{int(ftp_watts * 0.75)} W",
            "Z3_Tempo": f"{int(ftp_watts * 0.75)}-{int(ftp_watts * 0.90)} W",
            "Z4_Threshold": f"{int(ftp_watts * 0.90)}-{int(ftp_watts * 1.05)} W",
            "Z5_VO2Max": f"> {int(ftp_watts * 1.05)} W",
        }

    if not result:
        return {"error": "Please provide either max_hr (BPM) or ftp_watts (Watts)."}

    return result


def get_outdoor_training_weather(city: str) -> Dict[str, Any]:
    """Fetches real current weather and outdoor training safety conditions for a city via Open-Meteo public API.

    Args:
        city: City name to check weather for (e.g. 'Boulder', 'Austin', 'San Francisco').

    Returns:
        A dictionary containing real temperature (°F), wind speed (mph), humidity (%), and a triathlon training recommendation.
    """
    import json
    import urllib.parse
    import urllib.request

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        req = urllib.request.Request(
            geo_url, headers={"User-Agent": "TriCoachAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return {"error": f"Could not find coordinates for location '{city}'."}

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        resolved_name = f"{location.get('name')}, {location.get('admin1', '')} {location.get('country_code', '')}".strip()

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&wind_speed_unit=mph&temperature_unit=fahrenheit"
        req2 = urllib.request.Request(
            weather_url, headers={"User-Agent": "TriCoachAI/1.0"}
        )
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            weather_data = json.loads(resp2.read().decode())

        current = weather_data.get("current", {})
        temp_f = current.get("temperature_2m")
        wind_mph = current.get("wind_speed_10m")
        humidity = current.get("relative_humidity_2m")

        recommendation = "Great conditions for outdoor cycling or running!"
        if wind_mph and wind_mph > 20:
            recommendation = "High winds! Be cautious on aero bike setups or consider an indoor trainer ride."
        elif temp_f and temp_f > 85:
            recommendation = (
                "Hot conditions! Stay hydrated and plan your run/ride for early morning or evening."
            )
        elif temp_f and temp_f < 35:
            recommendation = "Freezing temperatures! Dress in layers or shift your session indoors."

        return {
            "location": resolved_name,
            "temperature_f": temp_f,
            "wind_speed_mph": wind_mph,
            "humidity_percent": humidity,
            "recommendation": recommendation,
        }
    except Exception as e:
        return {"error": f"Failed to fetch weather data: {str(e)}"}


async def generate_workout_artwork(
    prompt: str, tool_context: ToolContext
) -> Dict[str, Any]:
    """Generates custom triathlon training artwork or motivational badge using gemini-3.1-flash-lite-image in global region, saves it as a Playground artifact, and uploads it to public Cloud Storage.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'A motivational triathlon finisher badge with swim bike run icons').
        tool_context: ToolContext injected by ADK to save session artifacts.

    Returns:
        A dictionary containing the filename and the public Cloud Storage HTTPS URL of the image.
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    try:
        genai_client = genai.Client(
            vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        image_bytes = None
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
            if image_bytes:
                break

        if not image_bytes:
            return {"error": "Failed to generate image bytes from model response."}

        filename = f"artwork_{uuid.uuid4().hex[:8]}.jpg"

        # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "message": f"Successfully generated artwork and uploaded to public Cloud Storage URL: {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload artwork: {str(e)}"}


async def generate_workout_video(
    prompt: str, tool_context: ToolContext
) -> Dict[str, Any]:
    """Generates a short motivational triathlon training video using Google's Omni model (gemini-omni-flash-preview) in global region via the Interactions API, saves it as a Playground artifact, and uploads it to public Cloud Storage.

    Args:
        prompt: Detailed description of the video to generate (e.g. 'A 5-second video of a triathlete swimming in open water at sunrise').
        tool_context: ToolContext injected by ADK to save session artifacts.

    Returns:
        A dictionary containing the filename and the public Cloud Storage HTTPS URL of the video.
    """
    import base64
    import uuid
    from google import genai
    from google.genai import types as genai_types
    from google.cloud import storage

    try:
        genai_client = genai.Client(
            vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
        )
        
        # gemini-omni-flash-preview requires calling via the Interactions API with streaming
        stream = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["text", "video"],
            stream=True,
            timeout=180.0,
        )

        video_chunks = []
        mime_type = "video/mp4"

        for event in stream:
            # 1. Check delta content
            delta = getattr(event, "delta", None)
            if delta:
                content = getattr(delta, "content", None)
                if content:
                    ctype = getattr(content, "type", None)
                    if ctype == "video" or hasattr(content, "data"):
                        data = getattr(content, "data", None)
                        if getattr(content, "mime_type", None):
                            mime_type = content.mime_type
                        if data:
                            if isinstance(data, str):
                                video_chunks.append(base64.b64decode(data))
                            elif isinstance(data, bytes):
                                video_chunks.append(data)

            # 2. Check interaction output_video
            interaction = getattr(event, "interaction", None)
            if interaction:
                output_video = getattr(interaction, "output_video", None)
                if output_video:
                    data = getattr(output_video, "data", None)
                    if getattr(output_video, "mime_type", None):
                        mime_type = output_video.mime_type
                    if data and not video_chunks:
                        if isinstance(data, str):
                            video_chunks.append(base64.b64decode(data))
                        elif isinstance(data, bytes):
                            video_chunks.append(data)

            # 3. Check step model_output
            step = getattr(event, "step", None)
            if step:
                model_output = getattr(step, "model_output", None)
                if model_output:
                    contents = getattr(model_output, "content", []) or []
                    for c in contents:
                        ctype = getattr(c, "type", None)
                        if ctype == "video" or hasattr(c, "data"):
                            data = getattr(c, "data", None)
                            if getattr(c, "mime_type", None):
                                mime_type = c.mime_type
                            if data and not video_chunks:
                                if isinstance(data, str):
                                    video_chunks.append(base64.b64decode(data))
                                elif isinstance(data, bytes):
                                    video_chunks.append(data)

        video_bytes = b"".join(video_chunks)
        if not video_bytes:
            return {"error": "Failed to generate video bytes from Omni model response."}

        extension = "mp4"
        if "webm" in mime_type.lower():
            extension = "webm"
        filename = f"workout_video_{uuid.uuid4().hex[:8]}.{extension}"

        # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        artifact_part = genai_types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "message": f"Successfully generated workout video and uploaded to public Cloud Storage URL: {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload video: {str(e)}"}




