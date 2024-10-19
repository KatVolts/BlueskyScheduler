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

# File to store credentials
CREDENTIALS_FILE = "credentials.json"

# Global variables for Bluesky credentials
BLUESKY_SERVER = "https://bsky.social"
BLUESKY_HANDLE = ""
BLUESKY_PASSWORD = ""

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

# Function to upload media (image/gif/video)
def upload_media(access_token, filepath):
    mime_type, _ = mimetypes.guess_type(filepath)

    # Ensure it's an image or gif file
    if not mime_type or not mime_type.startswith("image/"):
        messagebox.showerror("Error", "Selected file is not a valid image or GIF. Please select an image or animated GIF (JPEG, PNG, GIF, etc.).")
        return None

    upload_url = f"{BLUESKY_SERVER}/xrpc/com.atproto.repo.uploadBlob"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": mime_type  # Set the correct MIME type (e.g., image/gif for GIFs)
    }

    with open(filepath, 'rb') as f:
        image_data = f.read()  # Read raw image or gif data

        response = requests.post(upload_url, headers=headers, data=image_data)

    # Check for a successful response
    if response.status_code == 200:
        return response.json()['blob']
    else:
        messagebox.showerror("Error", f"Media upload failed: {response.text}")
        return None

# Function to create a post
def post_to_bluesky(text, image_path=None, post_time=None):
    access_token, did = authenticate()
    if not access_token:
        return

    media_blob = None
    if image_path:
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
        payload['record']['embed'] = {
            "$type": "app.bsky.embed.images",
            "images": [{
                "image": media_blob,
                "alt": "Post image"
            }]
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
        path = filedialog.askopenfilename(
            title="Select Image/Video",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")]
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
