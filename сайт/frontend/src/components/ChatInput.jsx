import { ArrowUp } from 'lucide-react';



export default function ChatInput({

  value,

  onChange,

  onSubmit,

  loading,

  placeholder,

  compact = false,

}) {

  const canSend = value.trim().length >= 3 && !loading;



  const handleKeyDown = (e) => {

    if (e.key === 'Enter' && !e.shiftKey) {

      e.preventDefault();

      if (canSend) onSubmit();

    }

  };



  return (

    <div

      className={`relative flex items-end gap-2 rounded-[26px] border border-border/80 bg-card shadow-sm focus-within:border-foreground/20 transition-colors ${

        compact ? 'px-4 py-2.5' : 'px-4 py-3'

      }`}

    >

      <textarea

        rows={compact ? 1 : 1}

        value={value}

        onChange={(e) => onChange(e.target.value)}

        onKeyDown={handleKeyDown}

        placeholder={placeholder}

        className="flex-1 bg-transparent resize-none focus:outline-none text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground py-1.5 max-h-40 min-h-[24px]"

      />

      <button

        type="button"

        onClick={onSubmit}

        disabled={!canSend}

        className="shrink-0 w-8 h-8 rounded-full bg-foreground text-background flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"

        aria-label="Отправить"

      >

        <ArrowUp size={16} strokeWidth={2.5} />

      </button>

    </div>

  );

}

