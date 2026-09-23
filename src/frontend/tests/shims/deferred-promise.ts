type DeferredExecutor<T> = ((resolve: (value: T | PromiseLike<T>) => void, reject: (reason?: unknown) => void) => void) & {
  state: 'pending' | 'fulfilled' | 'rejected';
  result?: T;
  rejectionReason?: unknown;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
};

export function createDeferredExecutor<T>(): DeferredExecutor<T> {
  const executor = ((resolve, reject) => {
    executor.state = 'pending';
    executor.resolve = (value) => {
      if (executor.state !== 'pending') return;
      executor.result = value as T;
      executor.state = 'fulfilled';
      resolve(value);
    };
    executor.reject = (reason?: unknown) => {
      if (executor.state !== 'pending') return;
      executor.state = 'rejected';
      executor.rejectionReason = reason;
      reject(reason);
    };
  }) as DeferredExecutor<T>;
  return executor;
}

export class DeferredPromise<T> extends Promise<T> {
  private readonly executorState: DeferredExecutor<T>;
  readonly resolve: (value: T | PromiseLike<T>) => void;
  readonly reject: (reason?: unknown) => void;

  constructor(executor?: ((resolve: (value: T | PromiseLike<T>) => void, reject: (reason?: unknown) => void) => void) | null) {
    const deferredExecutor = createDeferredExecutor<T>();
    super((resolve, reject) => {
      deferredExecutor(resolve, reject);
      executor?.(deferredExecutor.resolve, deferredExecutor.reject);
    });
    this.executorState = deferredExecutor;
    this.resolve = deferredExecutor.resolve;
    this.reject = deferredExecutor.reject;
  }

  get state(): 'pending' | 'fulfilled' | 'rejected' {
    return this.executorState.state;
  }

  get rejectionReason(): unknown {
    return this.executorState.rejectionReason;
  }
}
