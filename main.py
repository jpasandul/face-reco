from picamera2 import Picamera2, controls
from picamera2.encoders import H264Encoder
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageEnhance
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
import os
from azure.storage.blob import BlobServiceClient
from azure.iot.device import IoTHubDeviceClient, Message
from dotenv import load_dotenv

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Reko App")
        
        # Load environment variables from .env
        load_dotenv()
        # Setup Azure Blob Storage client from secrets in the environment
        self.azure_storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.azure_blob_container = os.getenv("AZURE_BLOB_CONTAINER", "face-images")
        self.blob_service_client = BlobServiceClient.from_connection_string(self.azure_storage_connection_string)
        self.container_client = self.blob_service_client.get_container_client(self.azure_blob_container)
        
        # Setup Azure IoT Hub client from secrets in the environment
        self.iot_client = IoTHubDeviceClient.create_from_connection_string(os.getenv("AZURE_IOT_DEVICE_CONNECTION_STRING"))
        
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
        
        # Create directories if they don't exist
        self.original_dir = "originals"
        self.processed_dir = "pre-processed-data"
        self.color_faces_dir = os.path.join(self.processed_dir, "color")
        self.gray_faces_dir = os.path.join(self.processed_dir, "grayscale")
        os.makedirs(self.original_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.color_faces_dir, exist_ok=True)
        os.makedirs(self.gray_faces_dir, exist_ok=True)
        
        # Configure the camera for full resolution
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480)},  # Keep preview size smaller
            lores={"size": (320, 240), "format": "YUV420"}
        )
        self.capture_config = self.picam2.create_still_configuration(
            main={"size": (4056, 3040)}  # Full sensor resolution
        )
        
        # Start the camera in preview mode
        self.picam2.configure(self.preview_config)
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
        
        # Add detection status text
        self.detection_status = tk.Label(self.indicator_frame, text="Face Detection: Inactive", fg="gray")
        self.detection_status.pack(side=tk.LEFT, padx=5)
        
        # Create button frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=5)
        
        # Create buttons
        self.pause_button = tk.Button(self.button_frame, text="Pause Detection", command=self.toggle_detection)
        self.pause_button.pack(side=tk.LEFT)
        
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
            self.detection_status.config(text="Face Detection: Active", fg="green")
        else:
            # Solid gray when detection is paused
            color = 'gray'
            self.detection_status.config(text="Face Detection: Paused", fg="gray")
            
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

    def process_captured_image(self, original_path):
        # Read the full resolution image
        image = cv2.imread(original_path)
        
        # Convert to grayscale for initial face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces in the original image
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            print(f"No faces found in {original_path}")
            return None
        
        # Process the largest face (assuming it's the main subject)
        face = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = face
        
        # Add padding around the face (20%)
        padding = 0.2
        x = max(0, int(x - w * padding))
        y = max(0, int(y - h * padding))
        w = min(image.shape[1] - x, int(w * (1 + 2 * padding)))
        h = min(image.shape[0] - y, int(h * (1 + 2 * padding)))
        
        # Crop the face region first
        face_color = image[y:y+h, x:x+w]
        
        # Save paths for processing
        filename = os.path.basename(original_path)
        color_path = os.path.join(self.color_faces_dir, f"color_{filename}")
        gray_path = os.path.join(self.gray_faces_dir, f"gray_{filename}")
        
        # Start background processing
        import threading
        thread = threading.Thread(target=self.process_image_background, 
                                args=(face_color, color_path, gray_path))
        thread.start()
        
        return color_path, gray_path

    def process_image_background(self, face_color, color_path, gray_path):
        try:
            # Now apply enhancements only to the cropped face
            # Denoise the cropped image
            face_color = cv2.fastNlMeansDenoisingColored(face_color, None, 10, 10, 7, 21)
            
            # Convert to LAB color space for CLAHE
            lab = cv2.cvtColor(face_color, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # Merge channels back
            lab = cv2.merge((l,a,b))
            face_color = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Adjust contrast
            alpha = 1.3  # Contrast control
            beta = 0     # Brightness control
            face_color = cv2.convertScaleAbs(face_color, alpha=alpha, beta=beta)
            
            # Additional preprocessing from preprocess_image method
            face_color = cv2.resize(face_color, (224, 224))
            
            # Convert to PIL Image for additional enhancements
            face_color_pil = Image.fromarray(cv2.cvtColor(face_color, cv2.COLOR_BGR2RGB))
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(face_color_pil)
            face_color_pil = enhancer.enhance(1.3)  # Increase sharpness by 30%
            
            # Convert back to OpenCV format
            face_color = cv2.cvtColor(np.array(face_color_pil), cv2.COLOR_RGB2BGR)
            
            # Create grayscale version from the enhanced color face
            face_gray = cv2.cvtColor(face_color, cv2.COLOR_BGR2GRAY)
            face_gray = cv2.resize(face_gray, (224, 224))
            
            # Save the processed images
            cv2.imwrite(color_path, face_color)
            cv2.imwrite(gray_path, face_gray)
            
            print("Background processing completed successfully")
            
            # --- New Code: Upload and notify Azure ---
            # Upload the color processed image to Azure Blob storage
            color_blob_url = self.upload_to_blob(color_path)
            print(f"Uploaded to blob storage. URL: {color_blob_url}")

            # Send a message to Azure IoT Hub with the blob URL
            message = Message(f'{{"blob_url": "{color_blob_url}"}}')
            self.iot_client.send_message(message)
            print("IoT Hub message sent.")
            # ------------------------------------------
            
        except Exception as e:
            print(f"Error in background processing: {str(e)}")

    def preprocess_image(self, image):
        # Resize to standard size (e.g., 224x224 for many ML models)
        image = image.resize((224, 224), Image.Resampling.LANCZOS)
        
        # Convert to numpy array for normalization
        img_array = np.array(image).astype(float)
        
        # Normalize pixel values to [0, 1]
        img_array = img_array / 255.0
        
        # Enhance contrast
        image = Image.fromarray((img_array * 255).astype(np.uint8))
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)  # Increase contrast by 20%
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)  # Increase sharpness by 30%
        
        return image

    def capture_image_auto(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        
        self.picam2.stop()  # Stop before switching config
        self.picam2.configure(self.capture_config)
        self.picam2.start()
        
        self.picam2.capture_file(os.path.join(self.original_dir, filename))
        
        self.picam2.stop()  # Stop again before switching back
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        
        original_path = os.path.join(self.original_dir, filename)
        print(f"Original image saved as {filename}")
        self.status_label.config(text=f"Image captured: {filename}", fg="green")
        
        # Start processing and countdown immediately
        processed_paths = self.process_captured_image(original_path)
        
        if processed_paths:
            color_path, gray_path = processed_paths
            print(f"Processing started for:\nColor: {os.path.basename(color_path)}\nGrayscale: {os.path.basename(gray_path)}")
            self.status_label.config(text="Processing started...", fg="blue")
            
            # Start countdown immediately
            def start_countdown_sequence():
                self.countdown_active = True
                self.start_countdown(5)
            
            self.root.after(2000, start_countdown_sequence)
        else:
            print("Failed to detect face")
            self.status_label.config(text="Failed to detect face", fg="red")

    def capture_image(self):
        # Manual capture should also use the same processing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        
        # Capture full resolution image
        self.picam2.switch_mode_and_capture_file(
            self.capture_config,
            os.path.join(self.original_dir, filename)
        )
        
        # Switch back to preview configuration
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        
        original_path = os.path.join(self.original_dir, filename)
        processed_paths = self.process_captured_image(original_path)
        
        if processed_paths:
            color_path, gray_path = processed_paths
            messagebox.showinfo("Info", 
                f"Images saved:\nOriginal: {filename}\n"
                f"Color face: {os.path.basename(color_path)}\n"
                f"Grayscale face: {os.path.basename(gray_path)}")
        else:
            messagebox.showwarning("Warning", f"Original image saved as {filename}\nNo face detected for processing")
    
    def close_app(self):
        self.picam2.stop()
        self.root.destroy()

    def toggle_detection(self):
        self.detection_active = not self.detection_active
        if self.detection_active:
            self.pause_button.config(text="Pause Detection")
            self.status_label.config(text="Face detection resumed", fg="green")
        else:
            self.pause_button.config(text="Resume Detection")
            self.status_label.config(text="Face detection paused", fg="orange")
        
        # Reset detection variables when pausing
        if not self.detection_active:
            self.face_detected_time = None
            self.is_capture_pending = False
            self.waiting_for_next = False
            self.countdown_active = False

    def upload_to_blob(self, local_path):
        blob_name = os.path.basename(local_path)
        blob_client = self.container_client.get_blob_client(blob=blob_name)
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        return blob_client.url

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()