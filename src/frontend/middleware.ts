import { type NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('cognito_id_token')?.value;
  const isProtected = request.nextUrl.pathname.startsWith('/dashboard');
  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/jobs/:path*', '/profile/:path*', '/cv/:path*'],
};
