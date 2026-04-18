package exceptionIfazeMethodThrowUncheckedMutation;

import testing_lib.exceptionIfazeMethodThrowUncheckedMutation.ExceptionIfazeMethodThrowUncheckedMutation;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowUncheckedMutation constr = new ExceptionIfazeMethodThrowUncheckedMutation() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
