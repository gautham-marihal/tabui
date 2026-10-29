import React from "react";

const Footer: React.FC = () => {
  return (
    <footer>
      <div
        style={{
          display: "grid",
          placeItems: "center",
          marginTop: 20,
          marginBottom: 10,
          fontSize: 12,
        }}
      >
        © Copyright {new Date().getFullYear()} Tetherfi. All rights reserved.
      </div>
    </footer>
  );
};

export default Footer;
