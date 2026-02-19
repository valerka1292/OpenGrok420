import { Thought } from '../../../store/useChat';
import TimelineEvent from './TimelineEvent';

export default function Timeline({ events }: { events: Thought[] }) {
  return <div className="space-y-2">{events.map((e, i) => <TimelineEvent key={i} event={e} />)}</div>;
}
