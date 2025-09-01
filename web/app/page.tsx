import Header from "./components/Header";

export default function Home() {
  return (
    <div className="">
      <Header />
      <main className="mt-50 flex flex-col items-center justify-center">
        <a href="../downloads/Tutor-mac.zip" className="text-blue-500">Download</a>
        <p className="text-sm text-gray-500">First time? After installing, right-click the app and choose "Open".</p>
      </main>
    </div>
  );
}
