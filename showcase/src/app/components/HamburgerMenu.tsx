"use client";

import React from "react";
import Link from "next/link";

import { slide as Menu } from "react-burger-menu";

import { clerkConfigured, useSignedIn } from "@/lib/auth";

import "../css/HamburgerMenu.scss";

const HamburgerMenu: React.FC = () => {
  const { isSignedIn } = useSignedIn();
  // without sign-in set up nothing is protected, so every page is offered
  const mayOpen = (isProtected: boolean) => !isProtected || isSignedIn || !clerkConfigured;

  return (
    <Menu right width={"100%"}>
      <Link key={1} href={"/"}>
        Home
      </Link>

      {clerkConfigured && (
        <Link key={2} href={"/sign-in-out"}>
          {isSignedIn ? "Sign Out" : " Sign In"}
        </Link>
      )}

      <span key={3}>&nbsp;</span>

      {demoLinks.map(
        (element: {
          id: number;
          name: string;
          path: string;
          protected: boolean;
        }) => {
          const showLink = mayOpen(element.protected);

          return (
            showLink && (
              <Link key={element?.id} href={element?.path}>
                {element?.name}
              </Link>
            )
          );
        }
      )}

      <span key={5}>&nbsp;</span>

      {mayOpen(true) && (
        <Link key={4} href={"/recordings"}>
          Recordings
        </Link>
      )}
    </Menu>
  );
};

export default HamburgerMenu;

const demoLinks = [
  {
    id: 100,
    name: "Australian Bank HR Demo",
    path: "/ausbank-demo",
    protected: true,
  },
  {
    id: 200,
    name: "Auto Company Demo",
    path: "/autocompany-demo",
    protected: true,
  },
  {
    id: 300,
    name: "Singapore Health Demo",
    path: "/singapore-health-demo",
    protected: true,
  },
  {
    id: 400,
    name: "Self-Care Bank Demo",
    path: "/sc-bank-demo",
    protected: true,
  },
  {
    id: 500,
    name: "Bank CRM",
    path: "/crm",
    protected: true,
  },
];
