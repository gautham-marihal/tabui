import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// const isProtectedRoute = createRouteMatcher(['/dashboard(.*)', '/forum(.*)'])
const isProtectedRoute = createRouteMatcher([
  "/ausbank-demo",
  "/autocompany-demo",
  "/singapore-health-demo",
  "/sc-bank-demo",
  "/crm",
  "/recordings",
  "/api/s3(.*)",
]);

// clerkMiddleware() throws on every request (not just protected routes) once it's wired up as
// the default export, if its keys aren't set - which blocks local testing of any page, including
// unprotected ones like /nigeria-energy-demo. Skip Clerk entirely when unconfigured; any real
// deployment with real keys set behaves exactly as before.
const clerkConfigured = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
);

export default clerkConfigured
  ? clerkMiddleware(async (auth, req) => {
      if (isProtectedRoute(req)) await auth.protect();
    })
  : () => NextResponse.next();

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
