import Header from "../../components/Header";

export default function About() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>
      <div className="wireframe-grid"></div>
      <div className="wireframe-element"></div>
      <div className="wireframe-element"></div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <h1 className="text-2xl font-bold text-white">Manifesto here</h1>

      </main>
    </div>
  );
}