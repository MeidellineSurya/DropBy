import "./CapacityBar.css";

export function CapacityBar({ reserved, capacity }: { reserved: number; capacity: number }) {
  const pct = capacity > 0 ? Math.min(100, Math.round((reserved / capacity) * 100)) : 0;
  return (
    <div className="capacity-bar" title={`${reserved} / ${capacity} reserved`}>
      <div className="capacity-bar__track">
        <div className="capacity-bar__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="capacity-bar__label">
        {reserved}/{capacity}
      </span>
    </div>
  );
}
