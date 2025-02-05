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
        
        # Start the camera in preview mode
        self.picam2.configure(preview_config)
        self.picam2.start()
        
        # Create a label to display the camera feed
        self.label = tk.Label(root)
        self.label.pack()
        
        # Create indicator frame
        self.indicator_frame = tk.Frame(root)
        self.indicator_frame.pack(fill=tk.X, padx=5)
        
        # Add detection indicator
        self.detection_indicator = tk.Canvas(self.indicator_frame, width=20, height=20)
        self.detection_indicator.pack(side=tk.LEFT)
        self.indicator_dot = self.detection_indicator.create_oval(5, 5, 15, 15, fill='gray')
        
        # Create button frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=5)
        
        # Create buttons
        self.capture_button = tk.Button(self.button_frame, text="Capture Image", command=self.capture_image)
        self.capture_button.pack(side=tk.LEFT)
        
        # Add status label
        self.status_label = tk.Label(self.button_frame, text="No face detected", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.close_button = tk.Button(self.button_frame, text="Close", command=self.close_app)
        self.close_button.pack(side=tk.RIGHT)
        
        # Variables
        self.face_detected_time = None
        self.is_capture_pending = False
        self.waiting_for_next = False
        self.countdown_active = False
        self.detection_active = True
        self.indicator_state = False
        self.blink_indicator()
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
    
    def blink_indicator(self):
        if self.detection_active:
            # Blink green when detection is active
            color = 'green' if self.indicator_state else 'darkgreen'
        else:
            # Solid gray when detection is paused
            color = 'gray'
            
        self.detection_indicator.itemconfig(self.indicator_dot, fill=color)
        self.indicator_state = not self.indicator_state
        self.root.after(500, self.blink_indicator)  # Blink every 500ms

    def update_camera_feed(self):
        if self.picam2 is not None:
            # Capture a frame
            frame = self.picam2.capture_array()
            
            # Only perform face detection if detection is active
            if self.detection_active:
                # Create a smaller frame for face detection
                small_frame = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces on the smaller frame
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                
                # Scale the face coordinates back to original size
                scale_x = frame.shape[1] / small_frame.shape[1]
                scale_y = frame.shape[0] / small_frame.shape[0]
                
                current_time = time.time()
                
                if len(faces) > 0:
                    if not self.face_detected_time and not self.is_capture_pending:
                        # Face just detected, start the timer
                        self.face_detected_time = current_time
                        self.status_label.config(text="Face detected - Please stay still", fg="orange")
                    
                    if self.face_detected_time and not self.is_capture_pending:
                        time_since_detection = current_time - self.face_detected_time
                        if time_since_detection >= 2:
                            self.is_capture_pending = True
                            self.detection_active = False  # Pause detection
                            self.status_label.config(text="Capturing image...", fg="blue")
                            self.capture_image_auto()
                            self.face_detected_time = None
                else:
                    # Reset detection time if face is lost
                    self.face_detected_time = None
                    self.is_capture_pending = False
                    self.status_label.config(text="No face detected", fg="red")
                
                # Draw rectangles around faces
                for (x, y, w, h) in faces:
                    x, y, w, h = int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Convert frame for display
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(frame)
            self.photo = ImageTk.PhotoImage(image=frame)
            self.label.config(image=self.photo)
            self.label.image = self.photo
            
        self.root.after(10, self.update_camera_feed)
    
    def start_countdown(self, count):
        if count > 0:
            self.status_label.config(text=f"Next image capture starting in {count} seconds", fg="orange")
            self.root.after(1000, lambda: self.start_countdown(count - 1))
        else:
            self.countdown_active = False
            self.waiting_for_next = False
            self.detection_active = True  # Resume detection
            self.status_label.config(text="Ready for next person", fg="green")

    def capture_image_auto(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        self.picam2.capture_file(filename)
        print(f"Image saved as {filename}")
        self.status_label.config(text=f"Image captured: {filename}", fg="green")
        
        # Start the sequence of messages and timers
        def show_next_person():
            self.waiting_for_next = True
            self.status_label.config(text="Next person please", fg="blue")
            
            def start_countdown_sequence():
                self.countdown_active = True
                self.start_countdown(5)
            
            self.root.after(3000, start_countdown_sequence)
        
        self.root.after(3000, show_next_person)
    
    def capture_image(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        self.picam2.capture_file(filename)
        self.add_timestamp(filename)
        messagebox.showinfo("Info", f"Picture saved as {filename}")
    
    def close_app(self):
        self.picam2.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()