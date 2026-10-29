import { useEffect, useRef, useState } from "react";

interface ChatInputProps extends React.HTMLAttributes<HTMLFormElement> {
  onSend?: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({
  onSend,
  className,
  disabled,
  ...props
}: ChatInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string>("");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    props.onSubmit?.(e);
    onSend?.(message);
    setMessage("");
  };

  const isDisabled = disabled || message.trim().length === 0;

  useEffect(() => {
    if (disabled) return;
    // when not disabled refocus on input
    inputRef.current?.focus();
  }, [disabled]);

  return (
    <form
      {...props}
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        borderRadius: "0.375rem",
        paddingLeft: "0.25rem",
        fontSize: "0.875rem",
        lineHeight: "1.25rem",
      }}
    >
      <input
        autoFocus
        ref={inputRef}
        type="text"
        value={message}
        disabled={disabled}
        placeholder="Type something..."
        onChange={(e) => setMessage(e.target.value)}
        style={{
          padding: "10px 14px",
          flex: 1,
          minWidth: 0,
          border: "none",
          backgroundColor: "transparent",
          borderRadius: "10px",
          outline: "none",
        }}
        onFocus={(e) => {
          e.currentTarget.style.boxShadow =
            "0 0 0 0.5px rgba(255, 255, 255, 0.4)"; // semi-transparent blue
        }}
        onBlur={(e) => {
          e.currentTarget.style.boxShadow = "none";
        }}
      />
      <button
        // size="sm"
        style={{
          borderRadius: "10px",
          border: "none",
          padding: "10px 14px",
          alignItems: "center",
        }}
        type="submit"
        // variant={isDisabled ? 'secondary' : 'primary'}
        disabled={isDisabled}
        className="font-mono"
      >
        SEND
      </button>
    </form>
  );
}
