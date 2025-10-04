"use client";
import Link from "next/link";
import { useState, useEffect } from "react";

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [lastScrollY, setLastScrollY] = useState(0);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      if (currentScrollY > 100) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
      
      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  return (
    <>
    {/* Mobile Header - Fixed styling, always consistent */}
    <header className="sticky top-0 z-50 w-full bg-slate-200 backdrop-blur md:hidden">
      <div className="mx-auto flex h-14 items-center justify-between px-4">
        <Link href="/" className="text-2xl font-semibold tracking-tight text-gray-900">Scaffold</Link>

        {/* Hamburger menu button - Mobile only */}
        <button
          onClick={toggleMenu}
          className="relative w-8 h-8 flex flex-col justify-center items-center space-y-1.5 hover:bg-gray-50 rounded-md transition-colors duration-200 group"
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

      </div>
      
      {/* Mobile dropdown menu */}
      <div className={`absolute top-full left-0 right-0 overflow-hidden transition-all duration-300${
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
              <Link 
                href="../subscribe" 
                className="block text-gray-900 hover:text-gray-600 hover:bg-gray-50 transition-all text-lg py-3 px-2 rounded-md"
                onClick={toggleMenu}
              >
              Subscribe
            </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Desktop Header - Liquid glass component */}
      <header className="hidden md:block sticky top-0 w-full z-50 transition-all duration-300 ease-in-out">
        <div className={`flex transition-all duration-300 ease-in-out justify-center pt-10`}>
          <div className={`liquid-glass-header transition-all duration-300 ease-in-out ${
            isScrolled 
              ? 'w-[60px] h-2 px-2 py-1' 
              : 'w-[80%] h-20 px-12 py-6'
          } flex items-center ${isScrolled ? 'justify-center' : 'justify-between'}`}>
            {!isScrolled && (
              <Link href="/" className="glass-text font-semibold tracking-tight transition-all duration-300 text-2xl">
                Scaffold
              </Link>
            )}
            
            {/* Desktop navigation - only show when not scrolled */}
            {!isScrolled && (
              <nav className="flex items-center gap-8">
                <Link href="../about" className="glass-text text-lg hover:opacity-80 transition-opacity">
                  About
                </Link>
                <Link href="../contact" className="glass-text text-lg hover:opacity-80 transition-opacity">
                  Contact
                </Link>
                <Link href="../subscribe" className="glass-text text-lg hover:opacity-80 transition-opacity">
                  Subscribe
                </Link>
              </nav>
            )}
          </div>
        </div>
      </header>
    </>
  );
}