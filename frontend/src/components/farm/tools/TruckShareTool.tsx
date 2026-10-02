'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, PlusCircle, Truck, Users } from 'lucide-react';
import ToolSheet from './ToolSheet';
import { MandiPicker, PhonePicker } from './ContextPicker';
import { useToolSelection } from '@/context/ToolContext';
import { farmerApi } from '@/services/farmerApi';
import { formatDate } from '@/lib/format';

export default function TruckShareTool({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { mandiId, phone } = useToolSelection();
  const [showPost, setShowPost] = useState(false);
  const [travelDate, setTravelDate] = useState('');
  const [capacity, setCapacity] = useState('');
  const [joinQty, setJoinQty] = useState<Record<string, string>>({});
  const queryClient = useQueryClient();

  const { data, isFetching } = useQuery({
    queryKey: ['truck-trips', mandiId],
    queryFn: () => farmerApi.listTrips(mandiId),
    enabled: open,
  });

  const postMutation = useMutation({
    mutationFn: () => farmerApi.postTrip(mandiId, travelDate, Number(capacity), phone),
    onSuccess: () => {
      setShowPost(false);
      setTravelDate('');
      setCapacity('');
      queryClient.invalidateQueries({ queryKey: ['truck-trips', mandiId] });
    },
  });

  const joinMutation = useMutation({
    mutationFn: (tripId: string) => farmerApi.joinTrip(tripId, Number(joinQty[tripId] || 0), phone),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['truck-trips', mandiId] }),
  });

  const trips = data?.trips ?? [];

  return (
    <ToolSheet
      open={open}
      onClose={onClose}
      title="Truck Sharing"
      subtitle="Split a trip, split the transport cost"
      accentColour="#5c6b8a"
      icon={<Truck className="h-5 w-5" />}
    >
      <div className="space-y-4">
        <MandiPicker />
        <PhonePicker />

        <button
          type="button"
          onClick={() => setShowPost((v) => !v)}
          className="farm-focus flex items-center gap-1.5 text-sm font-bold text-[var(--leaf)]"
        >
          <PlusCircle className="h-4 w-4" /> {showPost ? 'Cancel' : 'Post a trip to this mandi'}
        </button>

        {showPost && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-2.5 rounded-xl border border-[var(--farm-line)] p-3.5"
          >
            <input
              type="date"
              value={travelDate}
              onChange={(event) => setTravelDate(event.target.value)}
              className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-sm font-semibold text-[var(--farm-ink)]"
            />
            <input
              type="number"
              min={1}
              value={capacity}
              onChange={(event) => setCapacity(event.target.value)}
              placeholder="Spare capacity (quintals)"
              className="farm-focus farm-tap w-full rounded-xl border border-[var(--farm-line)] bg-white px-3 text-sm font-semibold text-[var(--farm-ink)] placeholder:font-normal placeholder:text-[var(--farm-ink-faint)]"
            />
            <button
              disabled={!travelDate || !capacity || phone.length < 6 || postMutation.isPending}
              onClick={() => postMutation.mutate()}
              className="farm-focus farm-tap w-full rounded-xl text-sm font-bold text-white disabled:opacity-40"
              style={{ background: '#5c6b8a' }}
            >
              {postMutation.isPending ? 'Posting…' : 'Post trip'}
            </button>
          </motion.div>
        )}

        {isFetching && (
          <div className="flex items-center gap-2 py-6 text-sm text-[var(--farm-ink-faint)]">
            <Loader2 className="h-4 w-4 animate-spin" /> Looking for open trips…
          </div>
        )}

        {!isFetching && trips.length === 0 && (
          <p className="rounded-xl bg-[var(--farm-line)]/40 px-3.5 py-3 text-sm text-[var(--farm-ink-faint)]">
            No open trips to this mandi yet. Post one to start the board.
          </p>
        )}

        <div className="space-y-2.5">
          {trips.map((trip, index) => {
            const remaining = trip.total_capacity_quintals - trip.claimed_quintals;
            return (
              <motion.div
                key={trip.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06 }}
                className="rounded-2xl border border-[var(--farm-line)] p-3.5"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-[var(--farm-ink)]">{formatDate(trip.travel_date)}</p>
                    <p className="flex items-center gap-1 text-xs text-[var(--farm-ink-faint)]">
                      <Users className="h-3 w-3" /> {trip.posted_by_name} · {remaining} quintal(s) left
                    </p>
                  </div>
                </div>
                {remaining > 0 && (
                  <div className="mt-2.5 flex gap-2">
                    <input
                      type="number"
                      min={0.5}
                      max={remaining}
                      value={joinQty[trip.id] || ''}
                      onChange={(event) => setJoinQty((prev) => ({ ...prev, [trip.id]: event.target.value }))}
                      placeholder="Quintals to claim"
                      className="farm-focus min-w-0 flex-1 rounded-lg border border-[var(--farm-line)] px-2.5 py-2 text-sm placeholder:text-[var(--farm-ink-faint)]"
                    />
                    <button
                      disabled={!joinQty[trip.id] || phone.length < 6 || joinMutation.isPending}
                      onClick={() => joinMutation.mutate(trip.id)}
                      className="farm-focus shrink-0 rounded-lg px-3 text-sm font-bold text-white disabled:opacity-40"
                      style={{ background: 'var(--leaf)' }}
                    >
                      Join
                    </button>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </ToolSheet>
  );
}
