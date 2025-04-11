import React, { useState } from 'react';
import axios from 'axios';

import './App.css'

// Define types for the response
interface ScanResult {
  request_id: string;
  label: string;
  label_matched: boolean;
  debug_data?: string;
  message?: string;
  status?: string;
}

const App: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [requestId, setRequestId] = useState("");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Handle file input change
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedImage(event.target.files[0]);
    }
  };

  // Handle image upload
  const handleImageUpload = async () => {
    if (!selectedImage) {
      alert("Please select an image.");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setScanResult(null);

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64String = reader.result?.toString().split(',')[1] ?? '';

      const payload = {
        file: base64String,
        fileType: selectedImage.type,
        label: 'cat'
      };

      try {
        // Replace with your API Gateway URL for image upload
        const response = await axios.post(`${process.env.REACT_APP_BACKEND_API_URL}/scanrequest`, payload, {
        });

        // Assuming the backend returns a requestId and status message
        const { message, status } = response.data;

        setScanResult({message: message, status: status });
      } catch (error) {
        console.error("Error uploading the image:", error);
        setErrorMessage("Failed to upload image. Please try again.");
      } finally {
        setIsUploading(false);
      }
    };

    reader.readAsDataURL(selectedImage);
  };

  // Check status of the image processing based on Job ID
  const checkStatus = async () => {
    if (!requestId) {
      setErrorMessage("Please enter a valid Job ID.");
      return;
    }

    setIsCheckingStatus(true);
    setErrorMessage(null);

    try {
      // Replace with your API Gateway URL for checking status
      const apiUrl = `${process.env.REACT_APP_BACKEND_API_URL}/${requestId}`; 
      const response = await axios.get(apiUrl);

      const { containsCat, message } = response.data;
      setScanResult({
        requestId,
        containsCat,
        message,
        status: 'Completed',
      });
    } catch (error) {
      console.error("Error checking status:", error);
      setErrorMessage("Failed to check status. Please try again.");
    } finally {
      setIsCheckingStatus(false);
    }
  };

  return (
    <div className="App">
      <h1>Upload an Image for Cat Detection</h1>

      {/* File Upload */}
      <input
        type="file"
        id="image-upload"
        onChange={handleFileChange}
        style={{ display: 'none' }} // Hide the file input
      />
      <label htmlFor="image-upload" className="label-upload">
        'Choose Image'
      </label>

      {/* Display the selected file information */}
      {selectedImage && (
        <div className="file-info">
          <p>File Selected: <strong>{selectedImage.name}</strong></p>
          {selectedImage.type.startsWith('image') && (
            <img
              src={URL.createObjectURL(selectedImage)}
              alt="Preview"
              className="image-preview"
            />
          )}
        </div>
      )}

      {selectedImage && !isUploading && (
        <button onClick={handleImageUpload} disabled={isUploading}>
          {isUploading ? 'Uploading...' : 'Upload Image'}
        </button>
      )}

      {/* Display Error Messages */}
      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {/* Display Image Scan Result */}
      {scanResult && (
        <div className="result-container">
          <p>{scanResult.message}</p>
          <p>Status: {scanResult.status}</p>
          {scanResult.status === 'Processing' && (
            <button onClick={checkStatus} disabled={isCheckingStatus}>
              {isCheckingStatus ? 'Checking Status...' : 'Check Status'}
            </button>
          )}
          {scanResult.status === 'Completed' && (
            <p>{scanResult.label_matched ? 'This image contains a `${scanResult.labels}`' : 'No `${scanResult.labels}` detected in this image.'}</p>
          )}
        </div>
      )}

      {/* Check Status by Job ID */}
      <div className="check-status-container">
        <h2>Check Image Status by Job ID</h2>
        <input
          type="text"
          value={requestId}
          onChange={(e) => setrequestId(e.target.value)}
          placeholder="Enter Job ID"
          className="job-id-input"
        />
        <button onClick={checkStatus} disabled={isCheckingStatus}>
          {isCheckingStatus ? 'Checking Status...' : 'Get Status'}
        </button>
      </div>

      {/* Display Job ID after successful upload */}
      {requestId && !scanResult && !isUploading && (
        <div className="job-id-display">
          <p>Your Job ID: <strong>{requestId}</strong></p>
          <p>You can now check the status of your image processing using this Job ID.</p>
        </div>
      )}
    </div>
  );
}

export default App;
