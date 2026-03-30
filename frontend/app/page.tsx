'use client';

import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

interface FileStatus {
  file: File;
  id: string;
  status: 'PENDING' | 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  content?: string;
  error?: string;
}

export default function Dashboard() {
  const [files, setFiles] = useState<FileStatus[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).slice(0, 5).map(file => ({
        file,
        id: '',
        status: 'PENDING' as const
      }));
      setFiles(newFiles);
    }
  };

  const processFiles = async () => {
    for (let i = 0; i < files.length; i++) {
      const fileStatus = files[i];
      try {
        // 1. Get Presigned URL
        updateFileStatus(i, { status: 'UPLOADING' });
        const resUrl = await fetch(`${API_BASE_URL}/presigned-url`, {
          method: 'POST',
          body: JSON.stringify({ filename: fileStatus.file.name, contentType: fileStatus.file.type })
        });
        const { uploadUrl, fileId, key } = await resUrl.json();

        // 2. Upload to S3
        await fetch(uploadUrl, {
          method: 'PUT',
          body: fileStatus.file,
          headers: { 'Content-Type': fileStatus.file.type }
        });

        // 3. Start Extraction
        updateFileStatus(i, { status: 'PROCESSING', id: fileId });
        await fetch(`${API_BASE_URL}/start`, {
          method: 'POST',
          body: JSON.stringify({ fileId, key, bucket: process.env.NEXT_PUBLIC_BUCKET_NAME })
        });

        // 4. Poll for Status
        pollStatus(i, fileId);

      } catch (err: any) {
        updateFileStatus(i, { status: 'FAILED', error: err.message });
      }
    }
  };

  const pollStatus = async (index: number, fileId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/status/${fileId}`);
        const data = await res.json();

        if (data.status === 'COMPLETED') {
          updateFileStatus(index, { status: 'COMPLETED', content: data.content });
          clearInterval(interval);
        } else if (data.status === 'FAILED') {
          updateFileStatus(index, { status: 'FAILED', error: data.error });
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 2000);
  };

  const updateFileStatus = (index: number, update: Partial<FileStatus>) => {
    setFiles(prev => {
      const next = [...prev];
      next[index] = { ...next[index], ...update };
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Text Extractor Dashboard</h1>
        
        <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Upload className="w-10 h-10 mb-3 text-gray-400" />
                <p className="mb-2 text-sm text-gray-500 font-semibold">Click to upload or drag and drop</p>
                <p className="text-xs text-gray-400">PDF, DOCX, TXT, ZIP (Max 5 files)</p>
              </div>
              <input type="file" className="hidden" multiple onChange={handleFileChange} accept=".pdf,.docx,.txt,.zip" />
            </label>
          </div>
          <button 
            onClick={processFiles}
            className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            Extract Text
          </button>
        </div>

        <div className="space-y-4">
          {files.map((f, i) => (
            <div key={i} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FileText className="text-gray-400" />
                  <span className="font-medium text-gray-700">{f.file.name}</span>
                </div>
                <div className="flex items-center space-x-2">
                  {f.status === 'UPLOADING' && <Loader2 className="animate-spin text-blue-500" />}
                  {f.status === 'PROCESSING' && <Loader2 className="animate-spin text-orange-500" />}
                  {f.status === 'COMPLETED' && <CheckCircle className="text-green-500" />}
                  {f.status === 'FAILED' && <XCircle className="text-red-500" />}
                  <span className="text-sm font-medium">{f.status}</span>
                </div>
              </div>
              {f.content && (
                <pre className="mt-4 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-40">
                  {f.content}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
