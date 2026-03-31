'use client';

import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import JSZip from 'jszip';

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
  const [isZipping, setIsZipping] = useState(false);

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

  const uploadFile = async (index: number, currentFiles?: FileStatus[]) => {
    const list = currentFiles || files;
    const fileStatus = list[index];
    try {
      updateFileStatus(index, { status: 'UPLOADING' });
      const resUrl = await fetch(`${API_BASE_URL}/presigned-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: fileStatus.file.name, contentType: fileStatus.file.type })
      });
      const { uploadUrl, fileId, key } = await resUrl.json();

      await fetch(uploadUrl, {
        method: 'PUT',
        body: fileStatus.file,
        headers: { 'Content-Type': fileStatus.file.type }
      });

      updateFileStatus(index, { status: 'PROCESSING', id: fileId });
      await fetch(`${API_BASE_URL}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileId, key, bucket: process.env.NEXT_PUBLIC_BUCKET_NAME })
      });

      pollStatus(index, fileId);
    } catch (err: any) {
      updateFileStatus(index, { status: 'FAILED', error: err.message });
    }
  };

  const processFiles = async () => {
    await Promise.all(files.map((_, i) => uploadFile(i)));
  };

  const zipAndUpload = async () => {
    if (files.length === 0) return;
    setIsZipping(true);
    try {
      const zip = new JSZip();
      files.forEach(f => zip.file(f.file.name, f.file));
      const blob = await zip.generateAsync({ type: 'blob' });
      const zippedFile = new File([blob], 'extracted_batch.zip', { type: 'application/zip' });
      
      const zipStatus: FileStatus = {
        file: zippedFile,
        id: '',
        status: 'PENDING'
      };
      
      setFiles([zipStatus]);
      // Trigger upload for the new zip file
      setTimeout(() => uploadFile(0, [zipStatus]), 100);
    } catch (err) {
      console.error("Zipping error", err);
    } finally {
      setIsZipping(false);
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
      if (next[index]) {
        next[index] = { ...next[index], ...update };
      }
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
          <div className="flex space-x-4 mt-4">
            <button 
              onClick={processFiles}
              className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Upload Individually
            </button>
            <button 
              onClick={zipAndUpload}
              disabled={isZipping || files.length === 0}
              className="flex-1 bg-gray-800 text-white py-2 rounded-lg font-semibold hover:bg-black transition flex items-center justify-center"
            >
              {isZipping ? <Loader2 className="animate-spin mr-2" /> : null}
              Zip & Upload
            </button>
          </div>
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
                <pre className="mt-4 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                  {f.content}
                </pre>
              )}
              {f.error && (
                <p className="mt-2 text-sm text-red-500 font-medium">Error: {f.error}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
