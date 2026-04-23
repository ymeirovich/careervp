import { type NextRequest, NextResponse } from 'next/server';

const PROTECTED = ['/dashboard', '/applications', '/cv-center', '/billing', '/settings'];
const AUTH_PAGES = ['/login', '/register', '/confirm-signup', '/forgot-password', '/reset-password'];
const COOKIE = 'cognito_id_token';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(COOKIE)?.value;

  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
};
