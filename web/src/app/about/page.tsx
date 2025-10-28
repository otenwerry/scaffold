import Header from "../../components/Header";

export default function About() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <p className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          Scaffold only works on Macs with Apple chips right now. Compatibility with Intel chips and Windows machines coming later.
          The app only looks at your screen when you finish asking a question, and doesn’t save any of your data.
        </p>

      </main>
    </div>
  );
}