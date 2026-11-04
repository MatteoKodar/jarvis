import {useEffect, type ReactNode} from 'react';
import {X} from 'lucide-react';

type Props = {title: string; children: ReactNode; onClose: () => void};

export function Modal({title, children, onClose}: Props) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section role="dialog" aria-modal="true" aria-label={title} className="modal" onClick={event => event.stopPropagation()}>
        <header>
          <h2>{title}</h2>
          <button aria-label="Stäng" onClick={onClose}><X size={20}/></button>
        </header>
        {children}
      </section>
    </div>
  );
}
