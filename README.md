# Face Reko App 📸

## Overview
Face Reko App is a Python-based GUI application that detects faces in real-time using your Raspberry Pi camera. The app automatically captures images when a face is detected and processes them to extract both color and grayscale face regions. It leverages OpenCV for face detection, Picamera2 for image capture, and Pillow for post-processing enhancements.

## Features 😎
- **Real-Time Face Detection:** Continuously detects faces in the camera feed using Haar Cascade classifiers.
- **Automatic Image Capture:** Captures a full-resolution image automatically if a face is detected for more than 2 seconds.
- **Image Processing:** Enhances captured images by denoising, contrast adjustment, resizing, and additional enhancements. Processes and saves both color and grayscale versions of the detected face.
- **Manual Capture:** Allows you to capture images manually using a dedicated button.
- **User-Friendly GUI:** Built with Tkinter, featuring status updates, countdown timers, and visual indicators (blinking status).
- **Background Processing:** Uses threading for image processing so the UI remains responsive.

## How to Use 🚀

1. **Setup:**
   - Ensure your Raspberry Pi is connected to a compatible camera.
   - Install the required Python dependencies:
     ```bash
     pip install picamera2 opencv-python pillow numpy
     ```
   - Verify that the file `haarcascade_frontalface_default.xml` is in the same directory as the script.

2. **Directory Structure:**
   - The application automatically creates the following directories if they do not exist:
     - `originals` – for storing the original captured images.
     - `pre-processed-data/color` – for storing the processed color face images.
     - `pre-processed-data/grayscale` – for storing the processed grayscale face images.

3. **Running the Application:**
   - Launch the app by running:
     ```bash
     python main.py
     ```
   - A window will display the live camera feed with real-time face detection status and controls.

4. **Interacting with the Application:**
   - **Automatic Capture:** When a face is detected for over 2 seconds, an image is captured automatically.
   - **Manual Capture:** Click the **Capture Image** button to manually take a picture.
   - **Pause/Resume Detection:** Use the **Pause Detection** button to temporarily disable or resume face detection.
   - **Close the App:** Click the **Close** button to exit the application safely.

## Technical Details 🛠️
- **Picamera2:** Configures both a low-resolution preview and a full-resolution capture.
- **OpenCV:** Uses Haar Cascade classifiers for efficient face detection.
- **Tkinter:** Provides the GUI, which includes live video feed display and user interaction elements.
- **Image Processing:** Applies techniques such as denoising, Contrast Limited Adaptive Histogram Equalization (CLAHE), and brightness-contrast adjustments using OpenCV and Pillow.

## Troubleshooting & Tips 💡
- **Camera Issues:** Ensure that your camera is correctly connected and that the necessary drivers are installed.
- **Classifier File:** Verify that `haarcascade_frontalface_default.xml` is present and correctly referenced.
- **Directory Structure:** The `.gitignore` file is configured to ignore image files in the output directories while preserving the folder structure.

## License 📄
This project is open-source. Feel free to modify and use it according to your needs.

Happy coding! 😊 