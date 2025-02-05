from picamera2 import Picamera2, controls
from picamera2.encoders import H264Encoder
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi Camera Application")
        
        # Initialize the camera
        self.picam2 = Picamera2()
        self.encoder = H264Encoder()
        
        # Load the face cascade classifier
        cascade_path = 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise ValueError("Error loading face cascade classifier. Make sure the file exists.")
        
        # Face detection variables
        self.last_capture_time = 0
        self.capture_interval = 5  # seconds
        
        # Configure the camera with separate preview configuration
        preview_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480)},
            lores={"size": (320, 240), "format": "YUV420"}
        )
        self.capture_config = self.picam2.create_still_configuration(main={"size": (3280, 2464)})
        self.video_config = self.picam2.create_video_configuration(main={"size": (1920, 1080)})
        
        # Start the camera in preview mode
        self.picam2.configure(preview_config)
        self.picam2.start()
        
        # Create a label to display the camera feed
        self.label = tk.Label(root)
        self.label.pack()
        
        # Create buttons
        self.capture_button = tk.Button(root, text="Capture Image", command=self.capture_image)
        self.capture_button.pack(side=tk.LEFT)
        
        self.record_button = tk.Button(root, text="Start/Stop Recording", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT)
        
        self.close_button = tk.Button(root, text="Close", command=self.close_app)
        self.close_button.pack(side=tk.LEFT)
        
        # Variables
        self.is_recording = False
        self.update_camera_feed()
    
    def add_timestamp(self, image_path):
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        text_bbox = draw.textbbox((0, 0), timestamp, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = img.width - text_width - 10
        y = img.height - text_height - 10
        
        draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], fill='black')
        draw.text((x, y), timestamp, font=font, fill='white')
        img.save(image_path)
    
    def update_camera_feed(self):
        if self.picam2 is not None:
            # Capture a frame
            frame = self.picam2.capture_array()
            
            # Create a smaller frame for face detection
            small_frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces on the smaller frame
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Scale the face coordinates back to original size
            scale_x = frame.shape[1] / small_frame.shape[1]
            scale_y = frame.shape[0] / small_frame.shape[0]
            
            # Draw rectangle around faces and check if we should capture
            current_time = time.time()
            for (x, y, w, h) in faces:
                # Scale coordinates back to original size
                x, y, w, h = int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)
                
                # Draw rectangle around face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Check if we should capture an image
                if current_time - self.last_capture_time >= self.capture_interval:
                    self.capture_image_auto()
                    self.last_capture_time = current_time
            
            # Convert frame for display
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(frame)
            self.photo = ImageTk.PhotoImage(image=frame)
            self.label.config(image=self.photo)
            self.label.image = self.photo
        self.root.after(10, self.update_camera_feed)
    
    def capture_image_auto(self):
        if self.is_recording:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        self.picam2.capture_file(filename)
        self.add_timestamp(filename)
        print(f"Face detected - Picture saved as {filename}")  # Using print instead of messagebox for automatic capture
        
    def capture_image(self):
        if self.is_recording:
            messagebox.showinfo("Info", "Please stop recording first!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        self.picam2.capture_file(filename)
        self.add_timestamp(filename)
        messagebox.showinfo("Info", f"Picture saved as {filename}")
    
    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.video_filename = f"video_{timestamp}.h264"
            
            # Stop the current configuration and switch to video configuration
            self.picam2.stop()
            self.picam2.configure(self.video_config)
            self.picam2.start()
            
            # Start recording
            self.picam2.start_recording(self.encoder, self.video_filename)
            self.record_button.config(text="Stop Recording")
            messagebox.showinfo("Info", f"Started recording to {self.video_filename}")
        else:
            self.is_recording = False
            
            # Stop recording
            self.picam2.stop_recording()
            
            # Stop the current configuration and switch back to still image configuration
            self.picam2.stop()
            self.picam2.configure(self.capture_config)
            self.picam2.start()
            
            self.record_button.config(text="Start/Stop Recording")
            messagebox.showinfo("Info", "Recording stopped")
    
    def close_app(self):
        if self.is_recording:
            self.picam2.stop_recording()
        self.picam2.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()