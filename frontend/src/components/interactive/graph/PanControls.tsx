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
    <div className="absolute bottom-4 left-16 z-10 flex flex-col items-center gap-0.5 nodrag nopan">
      {/* Up Button */}
      <div className="bg-white border border-zinc-200 rounded shadow-sm">
        <button
          type="button"
          onClick={() => handlePan(0, 150)}
          className="w-7 h-7 flex items-center justify-center hover:bg-zinc-50 text-zinc-700 hover:text-zinc-950 transition-colors rounded focus:outline-none"
          title="Pan Up"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>

      {/* Row 2: Left, Down, Right */}
      <div className="flex bg-white border border-zinc-200 rounded shadow-sm divide-x divide-zinc-200">
        <button
          type="button"
          onClick={() => handlePan(150, 0)}
          className="w-7 h-7 flex items-center justify-center hover:bg-zinc-50 text-zinc-700 hover:text-zinc-950 transition-colors rounded-l focus:outline-none"
          title="Pan Left"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => handlePan(0, -150)}
          className="w-7 h-7 flex items-center justify-center hover:bg-zinc-50 text-zinc-700 hover:text-zinc-950 transition-colors focus:outline-none"
          title="Pan Down"
        >
          <ArrowDown className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => handlePan(-150, 0)}
          className="w-7 h-7 flex items-center justify-center hover:bg-zinc-50 text-zinc-700 hover:text-zinc-950 transition-colors rounded-r focus:outline-none"
          title="Pan Right"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default PanControls;
