package genericsClazzMethodTypeDeleteN;

import testing_lib.genericsClazzMethodTypeDeleteN.GenericsClazzMethodTypeDeleteN;

public class Main extends GenericsClazzMethodTypeDeleteN {

	public static void main(String[] args) {
		GenericsClazzMethodTypeDeleteN constr = new GenericsClazzMethodTypeDeleteN();
		constr.<Integer>method1();
	}

	@Override
	public <T> void method1() {

	}
}
