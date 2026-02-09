import React, { useState } from 'react';
import { X, ChevronRight, FileSpreadsheet, Database } from 'lucide-react';

interface WizardModalProps {
    onClose: () => void;
    onFileUpload: () => void;
    onConnectDB: (dbData: any) => Promise<void>;
}

export const WizardModal: React.FC<WizardModalProps> = ({ onClose, onFileUpload, onConnectDB }) => {
    const [showDBForm, setShowDBForm] = useState(false);
    const [dbData, setDbData] = useState({
        name: '',
        drivername: 'postgresql',
        host: '',
        port: 5432,
        database: '',
        username: '',
        password: ''
    });

    const handleDbConnect = async () => {
        if (!dbData.name || !dbData.host || !dbData.database || !dbData.username || !dbData.password) {
            alert('Please fill in all fields');
            return;
        }
        await onConnectDB(dbData);
        onClose();
    };
    return (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-xl flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
            <div className="w-full max-w-3xl bg-[#09090b] border border-white/10 rounded-[2rem] shadow-2xl relative overflow-hidden">

                {/* Modal Header */}
                <div className="p-8 border-b border-white/5 flex justify-between items-start bg-white/[0.02]">
                    <div>
                        <h2 className="text-2xl font-serif text-white mb-2">Configure New Uplink</h2>
                        <p className="text-slate-400 text-sm">Select a data protocol to initialize the agent.</p>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Modal Content */}
                <div className="p-10 grid grid-cols-2 gap-6">
                    <button
                        onClick={onFileUpload}
                        className="group p-8 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-emerald-500/50 transition-all text-left relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ChevronRight className="text-emerald-500" />
                        </div>
                        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
                            <FileSpreadsheet className="text-emerald-500" size={28} />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-2">Local File</h3>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Analyze spreadsheets (Excel, CSV) or Documents (PDF). Processed in-memory.
                        </p>
                    </button>

                    <button 
                        onClick={() => setShowDBForm(true)}
                        className="group p-8 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-blue-500/50 transition-all text-left relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ChevronRight className="text-blue-500" />
                        </div>
                        <div className="w-14 h-14 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
                            <Database className="text-blue-500" size={28} />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-2">Database Cluster</h3>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Connect read-only replica of Postgres or MySQL. Ideal for large datasets.
                        </p>
                    </button>
                </div>

                {/* Modal Footer */}
                {!showDBForm ? (
                    <div className="p-6 bg-black/40 border-t border-white/5 flex items-center justify-center">
                        <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-white/5 border border-white/5">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                            </span>
                            <span className="text-[10px] font-mono text-slate-300 uppercase tracking-widest">
                                Awaiting Selection
                            </span>
                        </div>
                    </div>
                ) : (
                    <div className="p-6 bg-black/40 border-t border-white/5 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Connection Name</label>
                                <input
                                    type="text"
                                    value={dbData.name}
                                    onChange={(e) => setDbData({...dbData, name: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="e.g., Production DB"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Driver</label>
                                <select
                                    value={dbData.drivername}
                                    onChange={(e) => setDbData({...dbData, drivername: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                >
                                    <option value="postgresql">PostgreSQL</option>
                                    <option value="mysql">MySQL</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Host</label>
                                <input
                                    type="text"
                                    value={dbData.host}
                                    onChange={(e) => setDbData({...dbData, host: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="127.0.0.1"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Port</label>
                                <input
                                    type="number"
                                    value={dbData.port}
                                    onChange={(e) => setDbData({...dbData, port: parseInt(e.target.value)})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="5432"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Database</label>
                                <input
                                    type="text"
                                    value={dbData.database}
                                    onChange={(e) => setDbData({...dbData, database: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="mydb"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-slate-400 mb-2 block">Username</label>
                                <input
                                    type="text"
                                    value={dbData.username}
                                    onChange={(e) => setDbData({...dbData, username: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="user"
                                />
                            </div>
                            <div className="col-span-2">
                                <label className="text-xs text-slate-400 mb-2 block">Password</label>
                                <input
                                    type="password"
                                    value={dbData.password}
                                    onChange={(e) => setDbData({...dbData, password: e.target.value})}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowDBForm(false)}
                                className="flex-1 px-4 py-2 rounded-lg border border-white/10 text-white text-sm hover:bg-white/5 transition-colors"
                            >
                                Back
                            </button>
                            <button
                                onClick={handleDbConnect}
                                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 transition-colors"
                            >
                                Connect
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};