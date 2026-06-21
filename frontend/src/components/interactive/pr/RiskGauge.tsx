import React from 'react';

interface Props {
  /** 0-100 score */
  score: number;
  /** Visible label above the ring (e.g. "Architecture Risk Score") */
  label: string;
  /** Optional level text rendered as the aria-label suffix and visible under the ring */
  level?: string;
  /** Override stroke color — default derives from score */
  stroke?: string;
  icon?: React.ReactNode;
  caption?: React.ReactNode;
}

const RADIUS = 60;
const CIRC = 2 * Math.PI * RADIUS;

function scoreColor(score: number): string {
  if (score > 75) return '#ef4444';
  if (score > 50) return '#f97316';
  if (score > 25) return '#eab308';
  return '#10b981';
}

/**
 * Accessible circular gauge — replaces 4 hand-rolled rings across
 * PRIntelligence / ArchitectureDrift / DeadCodeAnalyzer.
 */
export const RiskGauge: React.FC<Props> = ({
  score, label, level, stroke, icon, caption,
}) => {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const color = stroke ?? scoreColor(clamped);

  return (
    <div className="card-padded flex flex-col items-center text-center">
      <div className="panel-title mb-4">
        {icon}
        <span>{label}</span>
      </div>

      <div
        role="img"
        aria-label={`${label}: ${clamped} of 100${level ? `, ${level}` : ''}`}
        className="relative w-36 h-36 mb-3"
      >
        <svg className="w-full h-full -rotate-90" viewBox="0 0 144 144">
          <circle
            cx="72" cy="72" r={RADIUS}
            stroke="#1e293b" strokeWidth="10" fill="transparent"
          />
          <circle
            cx="72" cy="72" r={RADIUS}
            stroke={color} strokeWidth="10" fill="transparent"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={CIRC - (CIRC * clamped) / 100}
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold text-text font-mono tracking-tight">{clamped}</span>
          <span className="text-[10px] uppercase font-bold text-text-subtle tracking-wider">of 100</span>
        </div>
      </div>

      {caption}
    </div>
  );
};

export default RiskGauge;
