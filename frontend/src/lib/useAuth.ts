"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Auth guard hook: check for JWT token and redirect to /login if missing.
 */
export function useAuth() {
    const router = useRouter();
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (!token) {
            router.replace("/login");
        } else {
            setIsAuthenticated(true);
        }
        setLoading(false);
    }, [router]);

    const logout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        router.replace("/login");
    };

    const getToken = () => localStorage.getItem("token") || "";

    const getAuthHeaders = () => ({
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
    });

    return { isAuthenticated, loading, logout, getToken, getAuthHeaders };
}
