import Link from "next/link";
import React from "react";

import HamburgerMenu from "./HamburgerMenu";

const Header: React.FC = () => {
  return (
    <header style={{ zIndex: 1 }}>
      <div style={{ position: "relative" }} className="logo-container">
        <Link href="/">
          <img
            src="/images/tetherfi-logo.svg"
            alt="Tetherfi Logo"
            className="tetherfi-logo"
          />
        </Link>
      </div>

      <div className="title-container">
        <span>Tetherfi MX Bots</span>
      </div>

      <div className="hm-container">
        <HamburgerMenu />
      </div>
    </header>
  );
};

export default Header;
