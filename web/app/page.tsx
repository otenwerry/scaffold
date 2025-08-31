import Image from "next/image";
import Header from "./components/Header";

export default function Home() {
  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <Header />
      <main>
        <a href="../downloads/Tutor-mac.zip" className="text-blue-500">Download</a>
        <p className="text-sm text-gray-500">First time? After installing, right-click the app and choose "Open".</p>
      </main>
    </div>
  );
}
