export async function until<T>(callback: () => Promise<T>): Promise<[Error, null] | [null, T]> {
  try {
    return [null, await callback()];
  } catch (error) {
    return [error instanceof Error ? error : new Error(String(error)), null];
  }
}
