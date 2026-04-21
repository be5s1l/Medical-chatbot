/** Animated typing indicator used while the AI responds. */
import styles from "./typing.module.css";

export function TypingIndicator() {
  return (
    <div className={styles.wrap} aria-label="MediBot is typing">
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </div>
  );
}

