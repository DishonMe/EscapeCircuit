import { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

interface TimerProps {
  initialTime: number; // in seconds
}

export function Timer({ initialTime }: TimerProps) {
  const [timeLeft, setTimeLeft] = useState(initialTime);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 0) {
          if (!isExpired) {
            setIsExpired(true);
          }
          return prev + 1; // Start counting up
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isExpired]);

  const formatTime = (seconds: number) => {
    const absSeconds = Math.abs(seconds);
    const mins = Math.floor(absSeconds / 60);
    const secs = absSeconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimerColor = () => {
    if (timeLeft <= 0) return 'text-red-600';
    const percentage = (timeLeft / initialTime) * 100;
    if (percentage <= 10) return 'text-red-600';
    if (percentage <= 20) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <div className="flex items-center gap-2">
      <Clock className={`w-4 h-4 ${getTimerColor()}`} />
      <span className={`font-mono ${getTimerColor()}`}>
        {timeLeft < 0 ? '+' : ''}
        {formatTime(timeLeft)}
      </span>
    </div>
  );
}
