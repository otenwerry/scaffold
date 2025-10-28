import Header from "../../components/Header";

export default function Subscribe() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <h1 className="text-2xl font-bold text-white">Subscribe goes here</h1>
      </main>

    </div>
  );
}