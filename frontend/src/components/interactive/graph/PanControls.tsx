import React, { useCallback } from 'react';
import { useReactFlow } from 'reactflow';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';

export const PanControls: React.FC = () => {
  const { getViewport, setViewport } = useReactFlow();

  const handlePan = useCallback((dx: number, dy: number) => {
    const { x, y, zoom } = getViewport();
    setViewport({ x: x + dx, y: y + dy, zoom }, { duration: 200 });
  }, [getViewport, setViewport]);

  return (
    <div className="absolute bottom-4 left-16 z-10 flex flex-col items-center gap-1 nodrag nopan select-none">
      {/* Up Button */}
      <div className="bg-surface-2 border border-border rounded-lg shadow-float">
        <button
          type="button"
          onClick={() => handlePan(0, 150)}
          className="w-7.5 h-7.5 flex items-center justify-center hover:bg-canvas text-text-muted hover:text-text transition-colors rounded-lg focus:outline-none"
          title="Pan Up"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>

      {/* Row 2: Left, Down, Right */}
      <div className="flex bg-surface-2 border border-border rounded-lg shadow-float divide-x divide-border">
        <button
          type="button"
          onClick={() => handlePan(150, 0)}
          className="w-7.5 h-7.5 flex items-center justify-center hover:bg-canvas text-text-muted hover:text-text transition-colors rounded-l-lg focus:outline-none"
          title="Pan Left"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => handlePan(0, -150)}
          className="w-7.5 h-7.5 flex items-center justify-center hover:bg-canvas text-text-muted hover:text-text transition-colors focus:outline-none"
          title="Pan Down"
        >
          <ArrowDown className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => handlePan(-150, 0)}
          className="w-7.5 h-7.5 flex items-center justify-center hover:bg-canvas text-text-muted hover:text-text transition-colors rounded-r-lg focus:outline-none"
          title="Pan Right"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default PanControls;
