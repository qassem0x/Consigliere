import React, { useState } from 'react';
import { X, Shield, Settings, FileText } from 'lucide-react';

interface ChatSettings {
    zero_leaks_mode: boolean;
    max_row_limit: number;
    custom_prompt?: string;
}

interface ChatSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    settings: ChatSettings;
    onSave: (settings: ChatSettings) => void;
}

export const ChatSettingsModal: React.FC<ChatSettingsModalProps> = ({
    isOpen,
    onClose,
    settings,
    onSave
}) => {
    const [localSettings, setLocalSettings] = useState<ChatSettings>(settings);

    React.useEffect(() => {
        setLocalSettings(settings);
    }, [settings]);

    if (!isOpen) return null;

    const handleSave = () => {
        onSave(localSettings);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center">
            <div 
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />
            
            <div className="relative w-full max-w-lg bg-[#1a1a1e] border border-white/10 rounded-xl shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                    <div className="flex items-center gap-2">
                        <Settings size={18} className="text-primary" />
                        <h2 className="text-base font-semibold text-white">Chat Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="p-5 space-y-5">
                    <div>
                        <label className="text-xs text-slate-400 mb-2 block">Max Row Limit</label>
                        <input
                            type="number"
                            min="1"
                            max="100000"
                            value={localSettings.max_row_limit}
                            onChange={(e) => setLocalSettings({
                                ...localSettings, 
                                max_row_limit: parseInt(e.target.value) || 100
                            })}
                            className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                        />
                        <p className="text-[10px] text-slate-500 mt-1">
                            Maximum number of rows to return per query
                        </p>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/5">
                        <div className="flex items-center gap-3">
                            <Shield size={16} className="text-primary" />
                            <div>
                                <div className="text-sm text-white">Zero Leaks Mode</div>
                                <div className="text-[10px] text-slate-500">Prevent data leakage in responses</div>
                            </div>
                        </div>
                        <label className="cursor-pointer">
                            <input
                                type="checkbox"
                                checked={localSettings.zero_leaks_mode}
                                onChange={(e) => setLocalSettings({
                                    ...localSettings, 
                                    zero_leaks_mode: e.target.checked
                                })}
                                className="sr-only peer"
                            />
                            <div className="relative w-10 h-5 bg-white/10 rounded-full peer peer-checked:bg-primary transition-colors">
                                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
                            </div>
                        </label>
                    </div>

                    <div className="space-y-2">
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                            <FileText size={14} />
                            <span>Custom System Prompt</span>
                        </div>
                        <textarea
                            value={localSettings.custom_prompt || ''}
                            onChange={(e) => setLocalSettings({
                                ...localSettings, 
                                custom_prompt: e.target.value
                            })}
                            placeholder="Add custom instructions for the AI analyst..."
                            rows={5}
                            className="w-full px-3 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary resize-none font-mono"
                        />
                        <p className="text-[10px] text-slate-500">
                            This will be added to the system prompt
                        </p>
                    </div>
                </div>

                <div className="flex gap-3 px-5 py-4 border-t border-white/10">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 rounded-lg text-sm border border-white/10 text-slate-300 hover:bg-white/5 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        className="flex-1 px-4 py-2.5 rounded-lg text-sm bg-primary text-white hover:bg-primary/90 transition-colors font-medium"
                    >
                        Save Changes
                    </button>
                </div>
            </div>
        </div>
    );
};
