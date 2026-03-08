/**
 * 页面骨架屏组件
 * 用于页面数据加载时的占位显示，避免白屏
 */

export const PageHeaderSkeleton = () => (
  <div style={{ marginBottom: 32 }}>
    <div
      className="skeleton-shimmer"
      style={{
        width: 200,
        height: 32,
        marginBottom: 8,
        borderRadius: 6,
      }}
    />
    <div
      className="skeleton-shimmer"
      style={{
        width: 300,
        height: 16,
        borderRadius: 4,
      }}
    />
  </div>
)

export const CardSkeleton = ({ height = 400 }: { height?: number }) => (
  <div
    style={{
      background: 'rgba(30, 41, 59, 0.6)',
      borderRadius: 16,
      border: '1px solid rgba(148, 163, 184, 0.1)',
      padding: 24,
      height,
    }}
  >
    {/* Header */}
    <div
      className="skeleton-shimmer"
      style={{
        width: 150,
        height: 20,
        marginBottom: 24,
        borderRadius: 4,
      }}
    />
    {/* Content rows */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="skeleton-shimmer"
          style={{
            width: `calc(${Math.random() * 40 + 60}%)`,
            height: 16,
            borderRadius: 4,
          }}
        />
      ))}
    </div>
  </div>
)

export const TableSkeleton = () => (
  <div
    style={{
      background: 'rgba(30, 41, 59, 0.6)',
      borderRadius: 16,
      border: '1px solid rgba(148, 163, 184, 0.1)',
      padding: '24px 0',
    }}
  >
    {/* Table header */}
    <div
      style={{
        display: 'flex',
        gap: 16,
        padding: '0 24px 16px',
        borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
        marginBottom: 16,
      }}
    >
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="skeleton-shimmer"
          style={{
            flex: 1,
            height: 16,
            borderRadius: 4,
          }}
        />
      ))}
    </div>
    {/* Table rows */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '0 24px' }}>
      {[...Array(8)].map((_, rowIndex) => (
        <div key={rowIndex} style={{ display: 'flex', gap: 16 }}>
          {[...Array(6)].map((_, colIndex) => (
            <div
              key={colIndex}
              className="skeleton-shimmer"
              style={{
                flex: 1,
                height: 16,
                borderRadius: 4,
              }}
            />
          ))}
        </div>
      ))}
    </div>
  </div>
)

export const StatCardSkeleton = () => (
  <div
    style={{
      background: 'rgba(30, 41, 59, 0.6)',
      borderRadius: 16,
      border: '1px solid rgba(148, 163, 184, 0.1)',
      padding: 24,
    }}
  >
    <div
      className="skeleton-shimmer"
      style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        marginBottom: 16,
      }}
    />
    <div
      className="skeleton-shimmer"
      style={{
        width: 100,
        height: 36,
        marginBottom: 4,
        borderRadius: 4,
      }}
    />
    <div
      className="skeleton-shimmer"
      style={{
        width: 80,
        height: 14,
        borderRadius: 4,
      }}
    />
  </div>
)

// Full page skeleton layouts
export const DashboardSkeleton = () => (
  <div>
    <PageHeaderSkeleton />
    {/* Stats row */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, marginBottom: 32 }}>
      {[...Array(4)].map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
    {/* Charts row */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24, marginBottom: 32 }}>
      <CardSkeleton height={300} />
      <CardSkeleton height={300} />
    </div>
    {/* Recent tasks */}
    <CardSkeleton height={350} />
  </div>
)

export const TablePageSkeleton = () => (
  <div>
    <PageHeaderSkeleton />
    {/* Filter bar */}
    <div
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(20px)',
        borderRadius: 16,
        border: '1px solid rgba(148, 163, 184, 0.1)',
        padding: 24,
        marginBottom: 24,
      }}
    >
      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div className="skeleton-shimmer" style={{ width: 200, height: 32, borderRadius: 8 }} />
        <div className="skeleton-shimmer" style={{ width: 120, height: 32, borderRadius: 8 }} />
        <div className="skeleton-shimmer" style={{ width: 120, height: 32, borderRadius: 8 }} />
      </div>
    </div>
    {/* Table */}
    <TableSkeleton />
  </div>
)

export const DetailPageSkeleton = () => (
  <div>
    <PageHeaderSkeleton />
    <div style={{ marginBottom: 24 }}>
      <div className="skeleton-shimmer" style={{ width: 80, height: 32, borderRadius: 8 }} />
    </div>
    <CardSkeleton height={500} />
  </div>
)

export const FormPageSkeleton = () => (
  <div>
    <PageHeaderSkeleton />
    <div
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        borderRadius: 16,
        border: '1px solid rgba(148, 163, 184, 0.1)',
        padding: 32,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {[...Array(6)].map((_, i) => (
          <div key={i}>
            <div
              className="skeleton-shimmer"
              style={{
                width: 100,
                height: 16,
                marginBottom: 8,
                borderRadius: 4,
              }}
            />
            <div
              className="skeleton-shimmer"
              style={{
                width: '100%',
                height: 40,
                borderRadius: 8,
              }}
            />
          </div>
        ))}
      </div>
    </div>
  </div>
)

export default {
  PageHeader: PageHeaderSkeleton,
  Card: CardSkeleton,
  Table: TableSkeleton,
  StatCard: StatCardSkeleton,
  Dashboard: DashboardSkeleton,
  TablePage: TablePageSkeleton,
  DetailPage: DetailPageSkeleton,
  FormPage: FormPageSkeleton,
}
