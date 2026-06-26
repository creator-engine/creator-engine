# ce-ops#188 belt reviews-pickup claim bridge

- **Declared work class:** feature

Adds the belt claimability bridge for controller review-pickup items. The
controller review leg emits awaiting-review PR work as `kind: review_request`;
the generic belt claim/launch path now treats that shape as review work, exactly
like the per-seat `review_requested` Search feed shape.

The independent-reviewer guard now refuses self-review claims for both review
work-item kinds before posting any claim or assignee side effect. Successful
`review_request` claims launch a governed reviewer/review lane rather than the
default implementer lane.

Offline tests cover the controller `review_request` self-review refusal,
foreign-PR claimability, and reviewer-lane argv/seed mapping.
