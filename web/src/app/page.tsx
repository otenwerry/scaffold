import Header from "../components/Header";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen relative">
      <Header />
      
      <div className="wireframe-bg"></div>
      <div className="wireframe-grid"></div>
      <div className="wireframe-element"></div>
      <div className="wireframe-element"></div>
      <div className="wireframe-element"></div>
      
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <h1 className="text-6xl md:text-8xl font-bold text-white leading-tight">
            Scaffold
          </h1>

          <p className="text-xl md:text-2xl text-blue-200 max-w-2xl mx-auto leading-relaxed">
            Voice-based, context-aware AI tutor.
          </p>
          
          <div className="space-y-6 pt-8">
            <Button 
              asChild
              className="futuristic-button text-white text-lg px-8 py-4 h-auto"
            >
              <a href="../downloads/Tutor-mac.zip">
                Download
              </a>
            </Button>
            
            <p className="text-sm text-blue-300 max-w-md mx-auto">
              First time? After installing, right-click the app and choose "Open".
            </p>
          </div>
        </div>
      </main>

      {/* Additional content to test scrolling */}
      <section className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <h2 className="text-4xl md:text-6xl font-bold text-white leading-tight">
            Features
          </h2>
          <p className="text-lg md:text-xl text-blue-200 max-w-2xl mx-auto leading-relaxed">
            Experience the power of AI-driven learning with our advanced features.
          </p>
        </div>
      </section>

      <section className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <h2 className="text-4xl md:text-6xl font-bold text-white leading-tight">
            Get Started
          </h2>
          <p className="text-lg md:text-xl text-blue-200 max-w-2xl mx-auto leading-relaxed">
            Ready to transform your learning experience? Download now.
          </p>
        </div>
      </section>
    </div>
  );
}
