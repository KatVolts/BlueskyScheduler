import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
import requests
import json
import time
import threading
from PIL import Image
import os
import mimetypes

import moviepy.editor as mp  # Requires moviepy library for video length check


# File to store credentials
CREDENTIALS_FILE = "credentials.json"

# Global variables for Bluesky credentials
BLUESKY_SERVER = "https://bsky.social"
BLUESKY_HANDLE = ""
BLUESKY_PASSWORD = ""

# Function to upload video using Bluesky's video-specific API endpoint
def upload_video(access_token, filepath):
    mime_type, _ = mimetypes.guess_type(filepath)

    # Ensure it's a valid video file (Bluesky supports MP4, MOV, WEBM, and MPEG)
    if not mime_type or not mime_type.startswith("video/"):
        messagebox.showerror("Error", "Selected file is not a valid video. Please select a valid video file (MP4, MOV, WEBM, etc.).")
        return None

    # Check the video duration (must be under 60 seconds)
    max_video_length = 60  # 60 seconds
    video_length = check_video_duration(filepath)
    if video_length > max_video_length:
        messagebox.showerror("Error", f"Video exceeds the 60-second limit! Your video is {video_length:.2f} seconds.")
        return None

    # Check the file size (must be under 50 MB)
    max_file_size = 50 * 1024 * 1024  # 50 MB in bytes
    file_size = os.path.getsize(filepath)
    if file_size > max_file_size:
        messagebox.showerror("Error", f"File size exceeds the 50 MB limit! Your file size is {file_size / (1024 * 1024):.2f} MB.")
        return None

    upload_url = f"{BLUESKY_SERVER}/xrpc/app.bsky.video.uploadVideo"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": mime_type
    }

    with open(filepath, 'rb') as f:
        file_data = f.read()  # Read the entire file content as raw binary data

        response = requests.post(upload_url, headers=headers, data=file_data)

    if response.status_code == 200:
        return response.json()['blob']
    else:
        messagebox.showerror("Error", f"Video upload failed: {response.text}")
        return None

# Function to save credentials to a local file
def save_credentials():
    credentials = {
        "server": BLUESKY_SERVER,
        "handle": BLUESKY_HANDLE,
        "password": BLUESKY_PASSWORD
    }
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f)

# Function to load credentials from a local file
def load_credentials():
    global BLUESKY_SERVER, BLUESKY_HANDLE, BLUESKY_PASSWORD
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
            BLUESKY_SERVER = credentials.get("server", BLUESKY_SERVER)
            BLUESKY_HANDLE = credentials.get("handle", BLUESKY_HANDLE)
            BLUESKY_PASSWORD = credentials.get("password", BLUESKY_PASSWORD)

# Function to authenticate and retrieve session token
def authenticate():
    global BLUESKY_SERVER, BLUESKY_HANDLE, BLUESKY_PASSWORD
    auth_url = f"{BLUESKY_SERVER}/xrpc/com.atproto.server.createSession"
    payload = {
        "identifier": BLUESKY_HANDLE,
        "password": BLUESKY_PASSWORD
    }

    response = requests.post(auth_url, json=payload)
    if response.status_code == 200:
        session_data = response.json()
        return session_data['accessJwt'], session_data['did']
    else:
        messagebox.showerror("Error", f"Authentication failed: {response.text}")
        return None, None

# Function to check the video duration
def check_video_duration(filepath):
    video = mp.VideoFileClip(filepath)
    duration = video.duration  # Duration in seconds
    return duration

def upload_media(access_token, filepath):
    mime_type, _ = mimetypes.guess_type(filepath)

    if not mime_type:
        messagebox.showerror("Error", "Invalid file type. Please select an image or video.")
        return None

    # Handle image upload
    if mime_type.startswith("image/"):
        return upload_image(access_token, filepath)

    # Handle video upload
    if mime_type.startswith("video/"):
        return upload_video(access_token, filepath)

    messagebox.showerror("Error", "Unsupported media format.")
    return None


def post_to_bluesky(text, image_path=None, post_time=None):
    access_token, did = authenticate()
    if not access_token:
        return

    media_blob = None
    if image_path:
        mime_type, _ = mimetypes.guess_type(image_path)
        media_blob = upload_media(access_token, image_path)
        if not media_blob:
            return

    create_post_url = f"{BLUESKY_SERVER}/xrpc/com.atproto.repo.createRecord"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": {
            "text": text,
            "createdAt": post_time or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    }

    if media_blob:
        if mime_type.startswith("image/"):
            payload['record']['embed'] = {
                "$type": "app.bsky.embed.images",
                "images": [{"image": media_blob, "alt": "Post image"}]
            }
        elif mime_type.startswith("video/"):
            payload['record']['embed'] = {
                "$type": "app.bsky.embed.video",
                "video": [{"video": media_blob, "alt": "Post video"}]
            }

    response = requests.post(create_post_url, headers=headers, json=payload)
    if response.status_code == 200:
        messagebox.showinfo("Success", "Post submitted successfully!")
    else:
        messagebox.showerror("Error", f"Failed to post: {response.text}")


# Function to schedule the post
def schedule_post(text, image_path, post_time):
    current_time = time.time()
    delay = post_time - current_time
    threading.Timer(delay, post_to_bluesky, args=(text, image_path, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(post_time)))).start()
    messagebox.showinfo("Scheduled", "Post scheduled successfully!")

# Function to instantly post (Post Now)
def post_now():
    text = text_entry.get("1.0", "end-1c")
    image = image_path.get()
    if not text:
        messagebox.showerror("Error", "Post text cannot be empty!")
        return
    post_to_bluesky(text, image)

# Function to open the login window
def open_login_window():
    def submit_login():
        global BLUESKY_SERVER, BLUESKY_HANDLE, BLUESKY_PASSWORD
        BLUESKY_SERVER = server_entry.get()
        BLUESKY_HANDLE = handle_entry.get()
        BLUESKY_PASSWORD = password_entry.get()
        save_credentials()  # Save credentials to file
        login_window.destroy()

    login_window = tk.Toplevel()
    login_window.title("Login")

    tk.Label(login_window, text="Server:").grid(row=0, column=0)
    server_entry = tk.Entry(login_window)
    server_entry.insert(0, BLUESKY_SERVER)
    server_entry.grid(row=0, column=1)

    tk.Label(login_window, text="Username/Handle:").grid(row=1, column=0)
    handle_entry = tk.Entry(login_window)
    handle_entry.grid(row=1, column=1)

    tk.Label(login_window, text="Password:").grid(row=2, column=0)
    password_entry = tk.Entry(login_window, show="*")
    password_entry.grid(row=2, column=1)

    tk.Button(login_window, text="Submit", command=submit_login).grid(row=3, columnspan=2, pady=10)

# UI for the application
def create_ui():
    global text_entry, image_path

    root = tk.Tk()
    root.title("Bluesky Post Scheduler")

    # Load credentials at the start
    load_credentials()

    # Login button
    tk.Button(root, text="Login", command=open_login_window).pack(pady=10)

    # Input for post text
    tk.Label(root, text="Post Text:").pack()
    text_entry = tk.Text(root, height=5, width=50)
    text_entry.pack()

    # Button to upload image or video
    image_path = tk.StringVar()

    def upload_image():
        # Allow user to select both image and video files, showing all by default
        path = filedialog.askopenfilename(
            title="Select Image or Video",
            filetypes=[
                ("Media files", "*.png *.jpg *.jpeg *.gif *.mp4 *.mov *.avi *.webm"),  # Combined filter for images and videos
                ("Image files", "*.png *.jpg *.jpeg *.gif"),  # Separate filter for just images
                ("Video files", "*.mp4 *.mov *.avi *.webm"),  # Separate filter for just videos
                ("All files", "*.*")  # Option to show all files
            ]
        )
        image_path.set(path)


    tk.Button(root, text="Upload Image/Video", command=upload_image).pack()
    tk.Label(root, textvariable=image_path).pack()

    # Calendar for scheduling post
    tk.Label(root, text="Select Date and Time:").pack()
    cal = Calendar(root, selectmode='day')
    cal.pack(pady=10)

    # Time inputs
    time_frame = tk.Frame(root)
    tk.Label(time_frame, text="Hour (24h):").pack(side=tk.LEFT)
    hour_entry = tk.Entry(time_frame, width=5)
    hour_entry.pack(side=tk.LEFT)

    tk.Label(time_frame, text="Minute:").pack(side=tk.LEFT)
    minute_entry = tk.Entry(time_frame, width=5)
    minute_entry.pack(side=tk.LEFT)

    time_frame.pack()

    # Frame to hold the buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)

    # Button to schedule the post
    def submit_post():
        text = text_entry.get("1.0", "end-1c")
        image = image_path.get()
        selected_date = cal.selection_get()

        hour = int(hour_entry.get() or "0")
        minute = int(minute_entry.get() or "0")
        post_time = time.mktime(selected_date.timetuple()) + hour * 3600 + minute * 60

        if post_time < time.time():
            messagebox.showerror("Error", "Selected time is in the past!")
            return

        schedule_post(text, image, post_time)

    tk.Button(button_frame, text="Schedule Post", command=submit_post).grid(row=0, column=0, padx=10)

    # Button to instantly post
    tk.Button(button_frame, text="Post Now", command=post_now).grid(row=0, column=1, padx=10)

    root.mainloop()

if __name__ == "__main__":
    create_ui()
