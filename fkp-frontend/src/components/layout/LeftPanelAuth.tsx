import { motion } from "framer-motion"
import { Img } from 'react-image';
import { FKPProgress } from "./FKPProgress";

const leftVariants = {
  initial: { opacity: 0, x: -40 },
  animate: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.6 },
  },
}

const floatVariants = {
  animate: {
    y: [0, -10, 0],
    transition: { duration: 5, repeat: Infinity },
  },
}

const staggerContainer = {
  animate: {
    transition: { staggerChildren: 0.12, delayChildren: 0.2 },
  },
}

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5 },
  },
}

// ─── Feature Item ─────────────────────────────────────────────────────────────

interface FeatureItemProps {
  icon: string
  title: string
  description: string
}

function FeatureItem({ icon, title, description }: FeatureItemProps) {
  return (
    <motion.div variants={fadeUp} className="flex items-start gap-3">
      <div className="shrink-0 w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center text-lg">
        {icon}
      </div>
      <div>
        <p className="text-white text-sm font-medium leading-snug">{title}</p>
        <p className="text-white/55 text-xs mt-0.5 leading-relaxed">{description}</p>
      </div>
    </motion.div>
  )
}

// ─── Decorative Background ────────────────────────────────────────────────────

function LeftPanelBackground() {
  return (
    <>
      <div className="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-white/20 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-white/10 blur-3xl pointer-events-none" />
      <svg
        className="absolute inset-0 w-full h-full opacity-[0.08]"
        aria-hidden="true"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      <div className="absolute -bottom-20 -right-20 w-80 h-80 rounded-full border border-white/30 pointer-events-none" />
      <div className="absolute -bottom-28 -right-28 w-md h-112 rounded-full border border-white/20 pointer-events-none" />
    </>
  )
}

// ─── Left Panel ───────────────────────────────────────────────────────────────
export function LeftPanel() {
  return (
    <motion.div
      variants={leftVariants}
      initial="initial"
      animate="animate"
      className="hidden lg:flex flex-col relative w-[46%] xl:w-[50%] bg-[url('/assets/bg-auth.png')] bg-opacity-95 bg-cover bg-right p-12 overflow-hidden"
    >
      {/* Decorative background */}
      <LeftPanelBackground />

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-linear-to-b from-black/40 via-black/50 to-black/70" />

      {/* All content above overlay */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Logo */}
        <Img
          src={"/logo/logo.png"}
          className="w-32 h-auto"
          loader={<p>Loading...</p>}
        />

        {/* Main content */}
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="flex flex-col justify-end h-full gap-4"
        >
          <motion.div variants={fadeUp}>
            <p className="text-orange-300 text-xs font-medium tracking-widest uppercase">
              PT Sakti Pangan Perkasa
            </p>
            <h1 className="text-white text-3xl xl:text-4xl font-bold leading-tight">
              Formulir Keluhan Pelanggan
            </h1>
          </motion.div>

          <motion.p variants={fadeUp} className="text-white/60 text-sm leading-relaxed">
            Pantau proses pengajuan FKP Anda secara real-time, dari pengajuan hingga keputusan akhir.
          </motion.p>

          <div className="">
            <FKPProgress />
          </div>
        </motion.div>

      </div>
    </motion.div>
  )
}