import { motion, AnimatePresence } from 'framer-motion';
import { useRef, useState, useEffect, useCallback } from 'react';

interface AnimatedOTPInputProps {
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  maxLength?: number;
  disabled?: boolean;
  error?: boolean;
}

export default function AnimatedOTPInput({
  value,
  onChange,
  onComplete,
  maxLength = 6,
  disabled = false,
  error = false,
}: AnimatedOTPInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  // Focus first empty slot on mount
  useEffect(() => {
    if (!disabled) {
      const firstEmpty = value.length < maxLength ? value.length : maxLength - 1;
      inputRefs.current[firstEmpty]?.focus();
    }
  }, [disabled]); // eslint-disable-line react-hooks/exhaustive-deps

  const setChar = useCallback(
    (index: number, char: string) => {
      const chars = value.split('');
      chars[index] = char;
      const newValue = chars.join('').slice(0, maxLength);
      onChange(newValue);

      if (char && index < maxLength - 1) {
        inputRefs.current[index + 1]?.focus();
      }

      if (newValue.length === maxLength && onComplete) {
        onComplete(newValue);
      }
    },
    [value, maxLength, onChange, onComplete],
  );

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      e.preventDefault();
      if (value[index]) {
        // Clear current slot
        const chars = value.split('');
        chars[index] = '';
        onChange(chars.join('').replace(/\s+$/, ''));
      } else if (index > 0) {
        // Move back and clear previous
        const chars = value.split('');
        chars[index - 1] = '';
        onChange(chars.join('').replace(/\s+$/, ''));
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < maxLength - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleInput = (index: number, e: React.FormEvent<HTMLInputElement>) => {
    const inputValue = (e.target as HTMLInputElement).value;
    const digit = inputValue.replace(/\D/g, '').slice(-1);
    if (digit) {
      setChar(index, digit);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, maxLength);
    if (pastedData) {
      onChange(pastedData);
      const nextIndex = Math.min(pastedData.length, maxLength - 1);
      inputRefs.current[nextIndex]?.focus();
      if (pastedData.length === maxLength && onComplete) {
        onComplete(pastedData);
      }
    }
  };

  const half = Math.floor(maxLength / 2);

  return (
    <div className="otp-container" onPaste={handlePaste}>
      <div className="otp-group">
        {Array.from({ length: half }).map((_, i) => (
          <OTPSlot
            key={i}
            index={i}
            char={value[i] || ''}
            isFocused={focusedIndex === i}
            error={error}
            disabled={disabled}
            inputRef={(el) => { inputRefs.current[i] = el; }}
            onFocus={() => setFocusedIndex(i)}
            onBlur={() => setFocusedIndex(-1)}
            onInput={(e) => handleInput(i, e)}
            onKeyDown={(e) => handleKeyDown(i, e)}
          />
        ))}
      </div>

      <motion.div
        className="otp-separator"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.15 }}
      >
        <span>—</span>
      </motion.div>

      <div className="otp-group">
        {Array.from({ length: maxLength - half }).map((_, i) => {
          const idx = half + i;
          return (
            <OTPSlot
              key={idx}
              index={idx}
              char={value[idx] || ''}
              isFocused={focusedIndex === idx}
              error={error}
              disabled={disabled}
              inputRef={(el) => { inputRefs.current[idx] = el; }}
              onFocus={() => setFocusedIndex(idx)}
              onBlur={() => setFocusedIndex(-1)}
              onInput={(e) => handleInput(idx, e)}
              onKeyDown={(e) => handleKeyDown(idx, e)}
            />
          );
        })}
      </div>
    </div>
  );
}

function OTPSlot({
  index,
  char,
  isFocused,
  error,
  disabled,
  inputRef,
  onFocus,
  onBlur,
  onInput,
  onKeyDown,
}: {
  index: number;
  char: string;
  isFocused: boolean;
  error: boolean;
  disabled: boolean;
  inputRef: (el: HTMLInputElement | null) => void;
  onFocus: () => void;
  onBlur: () => void;
  onInput: (e: React.FormEvent<HTMLInputElement>) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}) {
  return (
    <motion.div
      className={
        'otp-slot' +
        (isFocused ? ' otp-slot-active' : '') +
        (error ? ' otp-slot-error' : '') +
        (char ? ' otp-slot-filled' : '')
      }
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, y: 0, scale: char ? 1.05 : 1 }}
      transition={{ duration: 0.2, delay: index * 0.05 }}
    >
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={1}
        value={char}
        disabled={disabled}
        className="otp-slot-input"
        onFocus={onFocus}
        onBlur={onBlur}
        onInput={onInput}
        onKeyDown={onKeyDown}
      />
      <AnimatePresence mode="wait">
        {char && (
          <motion.span
            key={char}
            className="otp-char"
            initial={{ opacity: 0, scale: 0.5, rotateY: -90 }}
            animate={{ opacity: 1, scale: 1, rotateY: 0 }}
            exit={{ opacity: 0, scale: 0.5, rotateY: 90 }}
            transition={{ duration: 0.2 }}
          >
            {char}
          </motion.span>
        )}
      </AnimatePresence>
      {isFocused && !char && (
        <motion.div
          className="otp-caret"
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}
