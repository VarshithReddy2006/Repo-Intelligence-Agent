import React, { useState } from 'react';
import { Folder, FolderOpen, FileCode, ChevronRight, ChevronDown } from 'lucide-react';

interface FileTreeProps {
  structure: Record<string, string[]>;
  onFileSelect?: (filePath: string) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({ structure, onFileSelect }) => {
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({
    'root': true,
    'src': true,
  });
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const toggleFolder = (folder: string) => {
    setOpenFolders(prev => ({
      ...prev,
      [folder]: !prev[folder]
    }));
  };

  const handleFileClick = (path: string) => {
    setSelectedFile(path);
    if (onFileSelect) {
      onFileSelect(path);
    }
  };

  // Extract all directories
  const directories = Object.keys(structure).sort((a, b) => {
    if (a === 'root' || a === '.') return -1;
    if (b === 'root' || b === '.') return 1;
    return a.localeCompare(b);
  });

  return (
    <div className="border border-border bg-card/30 rounded-lg p-4 font-mono text-sm h-[500px] overflow-y-auto w-full max-w-sm">
      <div className="text-xs uppercase tracking-wider text-text-muted font-bold mb-3 border-b border-border pb-2">
        Workspace Explorer
      </div>
      
      <div className="space-y-1">
        {directories.map((dir) => {
          const files = structure[dir] || [];
          const isRoot = dir === 'root' || dir === '.';
          const isOpen = openFolders[dir];

          return (
            <div key={dir} className="space-y-0.5">
              {/* Folder Header */}
              {!isRoot && (
                <div
                  onClick={() => toggleFolder(dir)}
                  className="flex items-center gap-1.5 py-1 px-1.5 rounded hover:bg-border/40 cursor-pointer text-text-muted select-none transition-colors"
                >
                  {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  {isOpen ? <FolderOpen className="h-4 w-4 text-primary" /> : <Folder className="h-4 w-4 text-primary" />}
                  <span className="text-text font-medium text-xs">{dir}</span>
                </div>
              )}

              {/* Folder Contents */}
              {(isRoot || isOpen) && (
                <div className={`${isRoot ? '' : 'pl-4 border-l border-border/30 ml-2'} space-y-0.5`}>
                  {files.map((file) => {
                    const fullPath = isRoot ? file : `${dir}/${file}`;
                    const isSelected = selectedFile === fullPath;

                    return (
                      <div
                        key={file}
                        onClick={() => handleFileClick(fullPath)}
                        className={`flex items-center gap-2 py-1 px-2 rounded cursor-pointer select-none text-xs transition-colors ${
                          isSelected
                            ? 'bg-primary/15 text-primary border-l-2 border-primary'
                            : 'hover:bg-border/30 text-text-muted hover:text-text'
                        }`}
                      >
                        <FileCode className={`h-3.5 w-3.5 ${isSelected ? 'text-primary' : 'text-text-muted/60'}`} />
                        <span>{file}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FileTree;
