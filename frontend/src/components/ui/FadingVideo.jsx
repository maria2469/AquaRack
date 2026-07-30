import { useEffect, useRef, useState } from "react";

/**
 * Autoplaying, muted background video that fades in on load and fades
 * out just before it ends. Accepts a single src or an array of srcs
 * that it cycles through.
 */
export default function FadingVideo({ src, className = "", style = {} }) {
  const videoRef = useRef(null);
  const opacityRef = useRef(0);
  const [, forceRender] = useState(0);
  const sources = Array.isArray(src) ? src : [src];
  const indexRef = useRef(0);

  const setOpacity = (v) => {
    opacityRef.current = v;
    if (videoRef.current) videoRef.current.style.opacity = String(v);
  };

  const animateOpacity = (from, to, duration) => {
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      setOpacity(from + (to - from) * t);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;

    const handleLoadedData = () => animateOpacity(opacityRef.current, 1, 500);

    const handleTimeUpdate = () => {
      if (!el.duration) return;
      const remaining = el.duration - el.currentTime;
      if (remaining <= 0.55 && opacityRef.current > 0) {
        animateOpacity(1, 0, 550);
      }
    };

    const handleEnded = () => {
      if (sources.length > 1) {
        indexRef.current = (indexRef.current + 1) % sources.length;
        forceRender((n) => n + 1);
      } else {
        el.currentTime = 0;
        el.play();
        animateOpacity(0, 1, 500);
      }
    };

    el.addEventListener("loadeddata", handleLoadedData);
    el.addEventListener("timeupdate", handleTimeUpdate);
    el.addEventListener("ended", handleEnded);

    return () => {
      el.removeEventListener("loadeddata", handleLoadedData);
      el.removeEventListener("timeupdate", handleTimeUpdate);
      el.removeEventListener("ended", handleEnded);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indexRef.current]);

  return (
    <video
      ref={videoRef}
      key={sources[indexRef.current]}
      className={className}
      style={{ opacity: 0, transition: "none", ...style }}
      src={sources[indexRef.current]}
      autoPlay
      muted
      playsInline
      preload="auto"
    />
  );
}