from picamera2 import Picamera2, controls
from picamera2.encoders import H264Encoder
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

def add_timestamp(image_path):
    # Open the image
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Try to load a font, fall back to default if not found
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # Calculate text size and position (bottom-right corner with padding)
    text_bbox = draw.textbbox((0, 0), timestamp, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Position text at bottom-right with 10px padding
    x = img.width - text_width - 10
    y = img.height - text_height - 10
    
    # Add black background for better readability
    draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], fill='black')
    
    # Add text in white
    draw.text((x, y), timestamp, font=font, fill='white')
    
    # Save the modified image
    img.save(image_path)

def main():
    # Initialize the camera
    picam2 = Picamera2()
    encoder = H264Encoder()
    
    # Try to enable noise reduction using multiple available controls
    try:
        # Configure both standard and RPi-specific noise reduction
        picam2.set_controls({
            "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality,
            "AwbEnable": True,
            "AeEnable": True,
            "FrameDurationLimits": (33333, 100000)  # Adjust exposure time limits
        })
        
        # Try to set camera tuning parameters
        camera_controls = {
            "SdnEnable": 1,            # Enable SDN
            "SdnStrength": 1.0,        # Set SDN strength
            "DenoiseLuma": 1.0,        # Luminance denoising
            "DenoiseChroma": 1.0       # Chrominance denoising
        }
        picam2.set_controls(camera_controls)
    except Exception as e:
        print(f"Note: Some advanced camera controls not supported: {e}")
    
    try:
        # Try to load custom tuning file
        picam2.camera_config = {
            "tuning": "imx219_tuning.yaml"  # Path to your tuning file
        }
    except Exception as e:
        print(f"Note: Custom tuning file not loaded: {e}")
    
    # Print camera properties
    print("\nCamera Properties:")
    print(f"Camera Model: {picam2.camera_properties['Model']}")
    
    print("\nSupported Sensor Modes:")
    for i, mode in enumerate(picam2.sensor_modes):
        print(f"Mode {i}: {mode['size']} - Format: {mode['format']}")
    print("\n")
    
    # Configure the camera with full resolution for IMX219 sensor (Pi Camera v2)
    capture_config = picam2.create_still_configuration(
        main={"size": (3280, 2464)},  # Native resolution for Pi Camera v2
        lores={"size": (640, 480)},   # Lower resolution for preview
        display="lores"
    )
    
    # Create video configuration
    video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},  # 1080p resolution
        lores={"size": (640, 480)},
        display="lores"
    )
    
    # Start with still capture configuration
    picam2.configure(capture_config)
    picam2.start()
    
    print("Pi Camera Test Program")
    print("Press '1' to take a picture")
    print("Press '2' to start/stop video recording")
    print("Press '3' to exit")
    print("Waiting for input...")
    
    is_recording = False
    
    while True:
        choice = input()
        
        if choice == '1':
            # Switch to still configuration if we were in video mode
            if is_recording:
                print("Please stop recording first!")
                continue
                
            if picam2.camera_configuration != capture_config:
                picam2.stop()
                picam2.configure(capture_config)
                picam2.start()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            
            # Capture and save the image at full resolution
            picam2.capture_file(filename)
            
            # Add timestamp to the image
            add_timestamp(filename)
            
            print(f"Picture saved as {filename}")
            print("Full resolution image captured (3280x2464) with timestamp")
            
        elif choice == '2':
            if not is_recording:
                # Switch to video configuration
                picam2.stop()
                picam2.configure(video_config)
                picam2.start()
                
                # Start recording
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_filename = f"video_{timestamp}.h264"
                picam2.start_recording(encoder, video_filename)
                print(f"Started recording to {video_filename}")
                print("Press '2' again to stop recording")
                is_recording = True
            else:
                # Stop recording
                picam2.stop_recording()
                print("Recording stopped")
                is_recording = False
                
                # Switch back to still configuration
                picam2.stop()
                picam2.configure(capture_config)
                picam2.start()
                
        elif choice == '3':
            if is_recording:
                print("Please stop recording first!")
                continue
            print("Exiting program...")
            break
            
        else:
            print("Invalid input. Press '1' for picture, '2' for video, or '3' to exit")
    
    # Stop the camera
    if is_recording:
        picam2.stop_recording()
    picam2.stop()

if __name__ == "__main__":
    main()