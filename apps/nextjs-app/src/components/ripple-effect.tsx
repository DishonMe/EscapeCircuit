/**
 * Ripple Effect component that animates from a point on drop.
 * Shows a radial ripple expanding and fading at the exact drop location.
 * 
 * Usage:
 *   <RippleEffect 
 *     x={100} 
 *     y={200} 
 *     key={Date.now()} 
 *   />
 */

export const RippleEffect = ({ x, y }: { x: number; y: number }) => {
  return (
    <>
      <style jsx>{`
        @keyframes workstation-ripple {
          0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 1;
          }
          100% {
            transform: translate(-50%, -50%) scale(2.5);
            opacity: 0;
          }
        }

        .ripple-pulse {
          animation: workstation-ripple 600ms cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
        }
      `}</style>
      <div
        className="ripple-pulse pointer-events-none absolute rounded-full border-2 border-cyan-400/70"
        style={{
          left: `${x}px`,
          top: `${y}px`,
          width: '24px',
          height: '24px',
          boxShadow: '0 0 12px rgba(34, 211, 238, 0.6)',
        }}
      />
    </>
  );
};
