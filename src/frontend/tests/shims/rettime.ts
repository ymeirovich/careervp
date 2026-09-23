type Listener = (event: Event) => void;

export class TypedEvent extends Event {
  constructor(type: string, init?: Record<string, unknown>) {
    super(type);
    if (init) Object.assign(this, init);
  }
}

export class Emitter {
  private readonly listeners = new Map<string, Set<Listener>>();

  on(type: string, listener: Listener): () => void {
    const listeners = this.listeners.get(type) ?? new Set<Listener>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
    return () => this.off(type, listener);
  }

  once(type: string, listener: Listener): () => void {
    const wrapped: Listener = (event) => {
      this.off(type, wrapped);
      listener(event);
    };
    return this.on(type, wrapped);
  }

  off(type: string, listener: Listener): void {
    this.listeners.get(type)?.delete(listener);
  }

  emit(event: Event | string, init?: Record<string, unknown>): void {
    const emitted = typeof event === 'string' ? new TypedEvent(event, init) : event;
    for (const listener of this.listenersFor(emitted.type)) {
      listener(emitted);
    }
  }

  async emitAsPromise(event: Event | string, init?: Record<string, unknown>): Promise<void> {
    const emitted = typeof event === 'string' ? new TypedEvent(event, init) : event;
    await Promise.all([...this.listenersFor(emitted.type)].map((listener) => listener(emitted)));
  }

  removeAllListeners(type?: string): void {
    if (type) {
      this.listeners.delete(type);
      return;
    }
    this.listeners.clear();
  }

  private listenersFor(type: string): Set<Listener> {
    return new Set([...(this.listeners.get(type) ?? []), ...(this.listeners.get('*') ?? [])]);
  }
}
