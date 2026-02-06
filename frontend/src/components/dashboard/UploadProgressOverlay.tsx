import React from 'react';
import { FileSpreadsheet, Cpu } from 'lucide-react';

interface UploadProgressOverlayProps {
    uploadProgress: {
        phase: 'uploading' | 'analyzing' | null;
        fileName?: string;
    };
}

export const UploadProgressOverlay: React.FC<UploadProgressOverlayProps> = ({ uploadProgress }) => {
    if (!uploadProgress.phase) return null;

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-50 animate-in fade-in duration-300">
            <div className="bg-[#09090b] border border-white/10 rounded-2xl p-12 max-w-md w-full shadow-2xl">
                {/* Animated Icon */}
                <div className="relative w-20 h-20 mx-auto mb-8">
                    <div className="absolute inset-0 border-4 border-rose-500/20 rounded-full"></div>
                    <div className="absolute inset-0 border-4 border-transparent border-t-rose-500 rounded-full animate-spin"></div>
                    <div className="absolute inset-3 flex items-center justify-center">
                        {uploadProgress.phase === 'uploading' ? (
                            <FileSpreadsheet className="text-rose-500" size={28} />
                        ) : (
                            <Cpu className="text-rose-500 animate-pulse" size={28} />
                        )}
                    </div>
                </div>

                {/* Status Text */}
                <div className="text-center space-y-3">
                    <h3 className="text-white font-bold text-lg">
                        {uploadProgress.phase === 'uploading' ? 'Secure Uplink' : 'Intelligence Processing'}
                    </h3>
                    <p className="text-slate-400 text-sm">
                        {uploadProgress.phase === 'uploading' 
                            ? `Encrypting and uploading ${uploadProgress.fileName}...`
                            : 'Initializing Data Agent for analysis...'}
                    </p>
                    
                    {/* Progress dots */}
                    <div className="flex items-center justify-center gap-1.5 pt-4">
                        <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce"></div>
                    </div>
                </div>
            </div>
        </div>
    );
};