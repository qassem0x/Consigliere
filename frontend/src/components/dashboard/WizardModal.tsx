import React, { useState, useRef } from 'react';
import { X, ChevronRight, ChevronLeft, FileSpreadsheet, Database, Shield, Check, Upload } from 'lucide-react';

interface FileSettings {
    title: string;
    zero_leaks_mode: boolean;
    max_row_limit: number;
}

interface WizardModalProps {
    onClose: () => void;
    onFileUpload: (file: File, settings: FileSettings) => void;
    onConnectDB: (dbData: any) => Promise<void>;
}

export const WizardModal: React.FC<WizardModalProps> = ({ onClose, onFileUpload, onConnectDB }) => {
    const [step, setStep] = useState<'select' | 'file-upload' | 'file-settings' | 'db-config' | 'db-settings'>('select');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [fileSettings, setFileSettings] = useState<FileSettings>({
        title: '',
        zero_leaks_mode: false,
        max_row_limit: 100
    });
    const [dbData, setDbData] = useState({
        name: '',
        title: '',
        drivername: 'postgresql',
        host: '',
        port: 5432,
        database: '',
        username: '',
        password: '',
        zero_leaks_mode: false,
        max_row_limit: 100
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setStep('file-settings');
        }
    };

    const handleFileUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileConfirm = () => {
        if (selectedFile) {
            onFileUpload(selectedFile, fileSettings);
            onClose();
        }
    };

    const handleDbConnect = async () => {
        if (!dbData.name || !dbData.host || !dbData.database || !dbData.username || !dbData.password) {
            alert('Please fill in all fields');
            return;
        }
        await onConnectDB(dbData);
        onClose();
    };

    const handleSelectFile = () => {
        setStep('file-upload');
    };

    const handleSelectDB = () => {
        setStep('db-config');
    };

    const handleDBConfigNext = () => {
        if (!dbData.name || !dbData.host || !dbData.database || !dbData.username || !dbData.password) {
            alert('Please fill in all fields');
            return;
        }
        setStep('db-settings');
    };

    const handleBack = () => {
        if (step === 'file-upload' || step === 'db-config') {
            setStep('select');
        } else if (step === 'file-settings') {
            setStep('file-upload');
        } else if (step === 'db-settings') {
            setStep('db-config');
        }
    };

    const getTitle = () => {
        switch (step) {
            case 'select': return 'Configure New Uplink';
            case 'file-upload': return 'Upload File';
            case 'file-settings': return 'File Settings';
            case 'db-config': return 'Database Connection';
            case 'db-settings': return 'Connection Settings';
        }
    };

    const getDescription = () => {
        switch (step) {
            case 'select': return 'Select a data protocol to initialize the agent.';
            case 'file-upload': return 'Select a file to analyze.';
            case 'file-settings': return 'Configure data retrieval settings.';
            case 'db-config': return 'Enter your database connection details.';
            case 'db-settings': return 'Configure data retrieval settings.';
        }
    };

    const renderStepIndicator = () => {
        if (step === 'select') return null;
        
        const isFile = step === 'file-upload' || step === 'file-settings';
        
        return (
            <div className="px-6 pt-4 flex items-center gap-2">
                <div className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step !== 'select' ? 'bg-primary text-primary-foreground' : 'bg-primary/20 text-primary'}`}>
                        <Check size={12} />
                    </div>
                    <span className="text-xs text-slate-400">{isFile ? 'File' : 'Connection'}</span>
                </div>
                <div className="flex-1 h-px bg-white/10" />
                <div className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step === 'file-settings' || step === 'db-settings' ? 'bg-primary text-primary-foreground' : 'bg-white/10 text-slate-500'}`}>
                        2
                    </div>
                    <span className="text-xs text-slate-400">Settings</span>
                </div>
            </div>
        );
    };

    const renderSettingsStep = (isFile: boolean, currentSettings: FileSettings, setSettings: React.Dispatch<React.SetStateAction<FileSettings>>, onConfirm: () => void) => (
        <div className="space-y-5">
            {isFile && selectedFile && (
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <FileSpreadsheet size={18} className="text-primary" />
                        </div>
                        <div className="flex-1">
                            <span className="text-xs font-medium text-white block">{selectedFile.name}</span>
                            <span className="text-[10px] text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</span>
                        </div>
                    </div>
                </div>
            )}

            {!isFile && (
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-3">
                        <Database size={14} className="text-primary" />
                        <span className="text-xs font-medium text-white">{dbData.name}</span>
                        <span className="text-[10px] text-slate-500">• {dbData.drivername}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                        {dbData.host}:{dbData.port}/{dbData.database}
                    </div>
                </div>
            )}

            <div className="space-y-4">
                <div>
                    <label className="text-xs text-slate-400 mb-1.5 block">Chat Title</label>
                    <input
                        type="text"
                        maxLength={100}
                        value={currentSettings.title}
                        onChange={(e) => setSettings({...currentSettings, title: e.target.value})}
                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                        placeholder="My Analysis"
                    />
                    <p className="text-[10px] text-slate-500 mt-1">Optional. Leave empty for auto-generated title.</p>
                </div>

                <div>
                    <label className="text-xs text-slate-400 mb-1.5 block">Max Row Limit</label>
                    <input
                        type="number"
                        min="1"
                        max="100000"
                        value={currentSettings.max_row_limit}
                        onChange={(e) => setSettings({...currentSettings, max_row_limit: parseInt(e.target.value) || 100})}
                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                        placeholder="100"
                    />
                    <p className="text-[10px] text-slate-500 mt-1">Maximum number of rows to retrieve from queries.</p>
                </div>

                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                            <Shield size={18} className="text-primary" />
                        </div>
                        <div className="flex-1">
                            <span className="text-sm text-white font-medium block mb-1">Zero Leaks Mode</span>
                            <p className="text-[10px] text-slate-400 leading-relaxed">
                                Enforced zero-leak privacy constraints, resulting in reduced summary quality as a trade-off. Use only for highly sensitive data
                            </p>
                            <label className="flex items-center gap-3 mt-3 cursor-pointer group">
                                <div className="relative">
                                    <input
                                        type="checkbox"
                                        checked={currentSettings.zero_leaks_mode}
                                        onChange={(e) => setSettings({...currentSettings, zero_leaks_mode: e.target.checked})}
                                        className="sr-only peer"
                                    />
                                    <div className="w-11 h-6 bg-white/10 rounded-full peer peer-checked:bg-primary transition-colors"></div>
                                    <div className="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full transition-transform peer-checked:translate-x-5"></div>
                                </div>
                                <span className="text-xs text-slate-300 group-hover:text-white transition-colors">
                                    {currentSettings.zero_leaks_mode ? 'Enabled' : 'Disabled'}
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex gap-3 pt-2">
                <button
                    onClick={handleBack}
                    className="flex-1 px-4 py-2.5 rounded-lg border border-white/10 text-white text-sm hover:bg-white/5 transition-colors flex items-center justify-center gap-2"
                >
                    <ChevronLeft size={16} />
                    Back
                </button>
                <button
                    onClick={onConfirm}
                    className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-white text-sm hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
                >
                    {isFile ? <Upload size={16} /> : <Database size={16} />}
                    {isFile ? 'Upload' : 'Connect'}
                </button>
            </div>
        </div>
    );

    return (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-xl flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
            <div className="w-full max-w-2xl bg-[#09090b] border border-white/10 rounded-[2rem] shadow-2xl relative overflow-hidden">

                {/* Modal Header */}
                <div className="p-6 border-b border-white/5 flex justify-between items-start bg-white/[0.02]">
                    <div>
                        <h2 className="text-xl font-serif text-white mb-1">{getTitle()}</h2>
                        <p className="text-xs text-slate-400">{getDescription()}</p>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Step Indicator */}
                {renderStepIndicator()}

                {/* Modal Content */}
                <div className="p-6">
                    {step === 'select' && (
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                onClick={handleSelectFile}
                                className="group p-6 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-primary/50 transition-all text-left relative overflow-hidden"
                            >
                                <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <ChevronRight className="text-primary" size={18} />
                                </div>
                                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-500">
                                    <FileSpreadsheet className="text-primary" size={24} />
                                </div>
                                <h3 className="text-white font-bold text-base mb-2">Local File</h3>
                                <p className="text-xs text-slate-400 leading-relaxed">
                                    Analyze spreadsheets (Excel, CSV) or Documents (PDF). Processed in-memory.
                                </p>
                            </button>

                            <button 
                                onClick={handleSelectDB}
                                className="group p-6 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-primary/50 transition-all text-left relative overflow-hidden"
                            >
                                <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <ChevronRight className="text-primary" size={18} />
                                </div>
                                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-500">
                                    <Database className="text-primary" size={24} />
                                </div>
                                <h3 className="text-white font-bold text-base mb-2">Database Cluster</h3>
                                <p className="text-xs text-slate-400 leading-relaxed">
                                    Connect read-only replica of Postgres or MySQL. Ideal for large datasets.
                                </p>
                            </button>
                        </div>
                    )}

                    {step === 'file-upload' && (
                        <div className="space-y-4">
                            <div 
                                onClick={handleFileUploadClick}
                                className="border-2 border-dashed border-white/10 rounded-2xl p-12 flex flex-col items-center justify-center cursor-pointer hover:border-primary/50 hover:bg-white/[0.02] transition-all"
                            >
                                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                                    <Upload className="text-primary" size={28} />
                                </div>
                                <span className="text-white font-medium mb-1">Click to select a file</span>
                                <span className="text-xs text-slate-400">Excel, CSV, or PDF</span>
                            </div>
                            <input 
                                ref={fileInputRef}
                                type="file" 
                                accept=".xlsx,.xls,.csv,.pdf"
                                onChange={handleFileChange}
                                className="hidden"
                            />
                            <button
                                onClick={handleBack}
                                className="w-full px-4 py-2.5 rounded-lg border border-white/10 text-white text-sm hover:bg-white/5 transition-colors flex items-center justify-center gap-2"
                            >
                                <ChevronLeft size={16} />
                                Back
                            </button>
                        </div>
                    )}

                    {step === 'file-settings' && renderSettingsStep(true, fileSettings, setFileSettings as React.Dispatch<React.SetStateAction<FileSettings>>, handleFileConfirm)}

                    {step === 'db-config' && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Connection Name</label>
                                    <input
                                        type="text"
                                        value={dbData.name}
                                        onChange={(e) => setDbData({...dbData, name: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="e.g., Production DB"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Driver</label>
                                    <select
                                        value={dbData.drivername}
                                        onChange={(e) => setDbData({...dbData, drivername: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                    >
                                        <option value="postgresql">PostgreSQL</option>
                                        <option value="mysql">MySQL</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Host</label>
                                    <input
                                        type="text"
                                        value={dbData.host}
                                        onChange={(e) => setDbData({...dbData, host: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="127.0.0.1"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Port</label>
                                    <input
                                        type="number"
                                        value={dbData.port}
                                        onChange={(e) => setDbData({...dbData, port: parseInt(e.target.value)})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="5432"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Database</label>
                                    <input
                                        type="text"
                                        value={dbData.database}
                                        onChange={(e) => setDbData({...dbData, database: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="mydb"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-slate-400 mb-1.5 block">Username</label>
                                    <input
                                        type="text"
                                        value={dbData.username}
                                        onChange={(e) => setDbData({...dbData, username: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="user"
                                    />
                                </div>
                                <div className="col-span-2">
                                    <label className="text-xs text-slate-400 mb-1.5 block">Password</label>
                                    <input
                                        type="password"
                                        value={dbData.password}
                                        onChange={(e) => setDbData({...dbData, password: e.target.value})}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-primary"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button
                                    onClick={handleBack}
                                    className="flex-1 px-4 py-2.5 rounded-lg border border-white/10 text-white text-sm hover:bg-white/5 transition-colors flex items-center justify-center gap-2"
                                >
                                    <ChevronLeft size={16} />
                                    Back
                                </button>
                                <button
                                    onClick={handleDBConfigNext}
                                    className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-white text-sm hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
                                >
                                    Next
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                    )}

                    {step === 'db-settings' && renderSettingsStep(false, { zero_leaks_mode: dbData.zero_leaks_mode, max_row_limit: dbData.max_row_limit }, (fn) => setDbData(prev => ({ ...prev, ...fn((s: any) => s) })), handleDbConnect)}
                </div>

                {/* Footer */}
                {step === 'select' && (
                    <div className="p-4 bg-black/40 border-t border-white/5 flex items-center justify-center">
                        <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-white/5 border border-white/5">
                            <span className="relative flex h-1.5 w-1.5">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
                            </span>
                            <span className="text-[10px] font-mono text-slate-300 uppercase tracking-widest">
                                Awaiting Selection
                            </span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
