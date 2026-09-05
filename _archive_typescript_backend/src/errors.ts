export class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "AppError";
  }
}

export const conflict = (code: string, message: string): AppError => new AppError(409, code, message);
export const forbidden = (code: string, message: string): AppError => new AppError(403, code, message);
export const notFound = (code: string, message: string): AppError => new AppError(404, code, message);
export const badRequest = (code: string, message: string): AppError => new AppError(400, code, message);
