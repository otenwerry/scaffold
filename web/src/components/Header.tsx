"use client";
import Link from "next/link";
import { useState } from "react";

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <>
    <header className="fixed top-0 z-50 w-full bg-white/70 backdrop-blur">
      <div className={`mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:h-16 sm:px-6  
        ${isMenuOpen ? "" : "border-b border-gray-100"}`}>
        <Link href="/" className="text-2xl font-semibold tracking-tight text-gray-900">Scaffold</Link>

        {/* Hamburger menu button, only visible on mobile and tablet */}
        <button
          onClick={toggleMenu}
          className="relative w-8 h-8 flex flex-col justify-center items-center space-y-1.5 hover:bg-gray-50 rounded-md transition-colors duration-200 group md:hidden"
          aria-label="Toggle menu"
        >
          <span 
            className={`w-6 h-0.5 bg-gray-900 transition-all duration-300 ${
              isMenuOpen ? 'rotate-45 translate-y-2' : ''
            }`}
          ></span>
          <span 
            className={`w-6 h-0.5 bg-gray-900 transition-all duration-300 ${
              isMenuOpen ? 'opacity-0' : ''
            }`}
          ></span>
          <span 
            className={`w-6 h-0.5 bg-gray-900 transition-all duration-300 ${
              isMenuOpen ? '-rotate-45 -translate-y-2' : ''
            }`}
          ></span>
        </button>

        {/* Desktop navigation - visible on larger screens */}
        <nav className="hidden items-center gap-6 md:flex">
          <Link href="../about" className="text-lg text-gray-600 hover:text-gray-900 transition-colors">
            About
          </Link>
          <Link href="../contact" className="text-lg text-gray-600 hover:text-gray-900 transition-colors">
            Contact
          </Link>
        </nav>
      </div>
      <div className={`md:hidden absolute top-full left-0 right-0 overflow-hidden transition-all duration-300${
          isMenuOpen ? 'max-h-96 opacity-100 translate-y-0' : 'max-h-0 opacity-0 -translate-y-2'
        }`}>
          <div className="bg-white/90 backdrop-blur border-b border-gray-100">
            <nav className="mx-auto max-w-6xl px-4 py-4 space-y-2">
              <Link 
                href="../about" 
                className="block text-gray-900 hover:text-gray-600 hover:bg-gray-50 transition-all text-lg py-3 px-2 rounded-md"
                onClick={toggleMenu}
              >
                About
              </Link>
              <Link 
                href="../contact" 
                className="block text-gray-900 hover:text-gray-600 hover:bg-gray-50 transition-all text-lg py-3 px-2 rounded-md"
                onClick={toggleMenu}
              >
                Contact
              </Link>
            </nav>
          </div>
        </div>
      </header>
    </>
  );
}