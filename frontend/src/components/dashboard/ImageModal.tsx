import React, { useEffect, useState } from 'react';
import { X, ZoomIn, ZoomOut, Download } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ImageModalProps {
    isOpen: boolean;
    imageUrl: string;
    altText?: string;
    onClose: () => void;
}

export const ImageModal: React.FC<ImageModalProps> = ({ isOpen, imageUrl, altText = "Image", onClose }) => {
    const [scale, setScale] = useState(1);
    const [isDragging, setIsDragging] = useState(false);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [startPos, setStartPos] = useState({ x: 0, y: 0 });

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setScale(1);
            setPosition({ x: 0, y: 0 });
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
            // slight delay to avoid flicker
            setTimeout(() => {
                setScale(1);
                setPosition({ x: 0, y: 0 });
            }, 300);
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    // Handle escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    if (!isOpen) return null;

    const handleZoomIn = (e: React.MouseEvent) => {
        e.stopPropagation();
        setScale(prev => Math.min(prev + 0.5, 4));
    };

    const handleZoomOut = (e: React.MouseEvent) => {
        e.stopPropagation();
        setScale(prev => {
            const newScale = Math.max(prev - 0.5, 1);
            if (newScale === 1) setPosition({ x: 0, y: 0 });
            return newScale;
        });
    };

    const handleDownload = (e: React.MouseEvent) => {
        e.stopPropagation();
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = `plot-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        if (scale > 1) {
            setIsDragging(true);
            setStartPos({ x: e.clientX - position.x, y: e.clientY - position.y });
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (isDragging && scale > 1) {
            e.preventDefault();
            const newX = e.clientX - startPos.x;
            const newY = e.clientY - startPos.y;
            setPosition({ x: newX, y: newY });
        }
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    const handleBackdropClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={handleBackdropClick}
        >
            {/* Toolbar */}
            <div
                className="absolute top-4 right-4 flex items-center gap-2 z-50"
                onClick={e => e.stopPropagation()}
            >
                <div className="bg-background/90 border rounded-lg shadow-sm flex items-center p-1">
                    <button
                        onClick={handleZoomIn}
                        className="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors text-muted-foreground hover:text-foreground"
                        title="Zoom In"
                    >
                        <ZoomIn size={20} />
                    </button>
                    <div className="w-px h-6 bg-border mx-1" />
                    <button
                        onClick={handleZoomOut}
                        className="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors text-muted-foreground hover:text-foreground"
                        disabled={scale <= 1}
                        title="Zoom Out"
                    >
                        <ZoomOut size={20} />
                    </button>
                    <div className="w-px h-6 bg-border mx-1" />
                    <button
                        onClick={handleDownload}
                        className="p-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-md transition-colors text-muted-foreground hover:text-foreground"
                        title="Download"
                    >
                        <Download size={20} />
                    </button>
                    <div className="w-px h-6 bg-border mx-1" />
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-md transition-colors"
                        title="Close"
                    >
                        <X size={20} />
                    </button>
                </div>
            </div>

            {/* Image Container */}
            <div
                className={cn(
                    "relative w-full h-full flex items-center justify-center p-8 overflow-hidden",
                    scale > 1 ? "cursor-grab active:cursor-grabbing" : "cursor-default"
                )}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onClick={e => e.stopPropagation()}
            >
                <img
                    src={imageUrl}
                    alt={altText}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl transition-transform duration-75"
                    style={{
                        transform: `scale(${scale}) translate(${position.x / scale}px, ${position.y / scale}px)`,
                    }}
                    draggable={false}
                />
            </div>
        </div>
    );
};
