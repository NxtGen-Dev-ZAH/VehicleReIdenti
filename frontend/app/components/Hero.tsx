"use client";

export function Hero() {
  return (
    <section className="relative min-h-[60vh] flex items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur">
      {/* Video Background */}
      <div className="absolute inset-0 z-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="h-full w-full object-cover opacity-90"
          onError={(e) => {
            // Fallback if video fails to load
            console.warn("Video failed to load, using gradient background");
            e.currentTarget.style.display = "none";
          }}
        >
          <source src="/VehicleVideo.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>
        {/* Overlay for better text readability */}
        <div className="absolute inset-0 bg-linear-to-br from-slate-950/80 via-slate-950/60 to-slate-950/80" />
        {/* Fallback gradient background */}
        <div className="absolute inset-0 bg-linear-to-br from-indigo-950/40 via-slate-950/60 to-slate-950/80" />
      </div>

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold tracking-tight text-slate-50 sm:text-5xl md:text-6xl lg:text-7xl">
          Vehicle Re-identification
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300 sm:text-xl md:text-2xl">
          Advanced AI-powered video analysis for vehicle tracking and
          re-identification in real-time and recorded footage
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="#upload"
            className="inline-flex items-center justify-center rounded-full bg-indigo-500 px-6 py-3 text-sm font-medium text-slate-50 transition-transform hover:bg-indigo-400 active:scale-95 shadow-sm"
          >
            Get Started
          </a>
          <a
            href="#about"
            className="inline-flex items-center justify-center rounded-full border border-slate-700 bg-slate-900/80 px-6 py-3 text-sm font-medium text-slate-100 transition-transform hover:bg-slate-800 active:scale-95 backdrop-blur"
          >
            Learn More
          </a>
        </div>
      </div>
    </section>
  );
}
