import React, { useState } from 'react';
import axios from 'axios';

import Loader from './components/Loader/Loader';
import './App.css'

// Define types for the response
interface ScanResult {
  request_id: string;
  label: string;
  label_matched: boolean;
  debug_data?: string;
  message?: string,
  status?: string;
}

// interface RequestResult {
//   requestId: string;
//   message: string;
//   status: string;
// }

const App: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [requestId, setRequestId] = useState("");
  const [inputLabel, setInputLabel] = useState("cat");
  const [isCheckingStatus, setIsCheckingStatus] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [includeDebugData, setIncludeDebugData] = useState(false);

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
    setIsLoading(true)
    setErrorMessage(null);
    setScanResult(null);

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64String = reader.result?.toString().split(',')[1] ?? '';

      const payload = {
        file: base64String,
        fileType: selectedImage.type,
        label: inputLabel
      };

      try {
        // Replace with your API Gateway URL for image upload
        const response = await axios.post(`${process.env.REACT_APP_BACKEND_API_URL}/scanrequest`, payload, {

        });

        setRequestId(response.data.request_id);
        
      } catch (error:any) {
        console.error("Error uploading the image:", error);
        setErrorMessage(error.response.data.message);
      } finally {
        setIsLoading(false);
      }
    };

    reader.readAsDataURL(selectedImage);
  };

      // Add this utility function at the top of your file
    const formatDebugData = (data: any): string => {
      try {
        if (typeof data === 'string') return data;
        if (!data) return 'No debug data available';
        return JSON.stringify(data, null, 2); // Pretty-print with 2-space indentation
      } catch (e) {
        return 'Could not format debug data';
      }
    };

  // Check status of the image processing based on Job ID
  const checkStatus = async () => {
    if (!requestId) {
      setErrorMessage("Please enter a valid Request ID.");
      return;
    }
    setIsLoading(true);
    setIsCheckingStatus(true);
    setErrorMessage(null);

    try {
      // Replace with your API Gateway URL for checking status
      const apiUrl = `${process.env.REACT_APP_BACKEND_API_URL}/scanrequest/${requestId}`; 
      const response = await axios.get(apiUrl, {
        params: {
          debugData: includeDebugData ? 'Y' : undefined
        }
      });
      setScanResult(response.data);

    } catch (error) {
      console.error("Error checking status:", error);
      setErrorMessage("Failed to check status. Please try again.");
    } finally {
      setIsCheckingStatus(false);
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      {isLoading && <Loader></Loader>}
      { !isLoading &&
      <>
      <h1>Upload an Image for Cat Detection</h1>

      {/* File Upload */}
      <input
        type="file"
        id="image-upload"
        onChange={handleFileChange}
        style={{ display: 'none' }} // Hide the file input
      />
      <label htmlFor="image-upload" className="stylish-upload-button">
        <span>📷 Choose Image</span>
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

      {selectedImage && (
        <button onClick={handleImageUpload} >
           'Upload Image'
        </button>
      )}

      <h2>Match this Label</h2>
        <input
          type="text"
          value={inputLabel}
          onChange={(e) => setInputLabel(e.target.value)}
          placeholder="Enter input label to be matched"
          className="job-id-input"
        />
      {/* Display Error Messages */}
      {errorMessage && <p className="error-message">{errorMessage}</p>}

      {/* Check Status by Job ID */}
      <div className="check-status-container">
        <h2>Check Image Status by Job ID</h2>
        <input
          type="text"
          value={requestId}
          onChange={(e) => setRequestId(e.target.value)}
          placeholder="Enter Job ID"
          className="job-id-input"
        />

        <label className="debug-checkbox">
        <input
          type="checkbox"
          checked={includeDebugData}
          onChange={(e) => setIncludeDebugData(e.target.checked)}
        />
        Include Debug Data
      </label>
        <button onClick={checkStatus} disabled={isCheckingStatus}>
          {isCheckingStatus ? 'Checking Status...' : 'Get Status'}
        </button>
      </div>

      {/* Display Job ID after successful upload */}
      {requestId && !scanResult && (
        <div className="job-id-display">
          <p>Your Job ID: <strong>{requestId}</strong></p>
          <p>You can now check the status of your image processing using this Job ID.</p>
        </div>
      )}

      {/* Display Image Scan Result */}
      {scanResult && (
        <div className="result-container">
          <p>{scanResult.message}</p>
          <p>Status: {scanResult.status}</p>
          {scanResult.status === 'completed' && (
            <p>
              {scanResult.label_matched 
                ? `This ${scanResult.request_id} image contains a ${scanResult.label}` 
                : `No ${scanResult.label} detected in this image request ${scanResult.request_id}.`}
            </p>

          )}

        {scanResult?.debug_data && (
          <div className="debug-content">
            <h4>Debug Information:</h4>
            <pre>{formatDebugData(scanResult.debug_data)}</pre>
          </div>
        )}
        </div>
      )}
      </>
    }
    </div>
  );
}

export default App;
